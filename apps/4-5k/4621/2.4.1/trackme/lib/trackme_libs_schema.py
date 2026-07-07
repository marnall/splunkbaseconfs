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

import os
import sys
import json
import logging
import random
import requests
import urllib3
import re
import time
import hashlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import Splunk libs
import splunklib.client as client
import splunklib.results as results

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_idx_for_tenant,
    trackme_vtenant_account_from_service,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, build_dhm_asset_list

# import croniter libs
from trackme_libs_croniter import cron_to_seconds

# import trackme libs
from trackme_libs import get_kv_collection

# import trackme libs get data
from trackme_libs_get_data import get_full_kv_collection

# import the collections dict
from collections_data import (
    collections_dict,
    vtenant_account_default,
    remote_account_default,
    wlk_default_thresholds,
)

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


# Function to format the version number
def trackme_schema_format_version(trackme_version: str) -> int:
    # Handle None case: if version retrieval failed, consider schema up to date
    # Return 0 to represent "no version info available, assume current schema is fine"
    # This prevents blocking logic: for positive schema versions, comparisons like
    # "schema_version < 0" will be False, avoiding unnecessary upgrade triggers
    if trackme_version is None:
        get_effective_logger().warning(
            "trackme_schema_format_version: trackme_version is None, version retrieval likely failed. "
            "Returning 0 to assume schema is up to date and avoid blocking logic."
        )
        # Return 0 to represent "assume current schema is up to date"
        # For typical positive schema versions (e.g., 20303), comparisons like
        # "schema_version < 0" will be False, preventing upgrade triggers
        return 0
    
    # Split the version into its components
    version_parts = trackme_version.split(".")
    
    # Validate version format: must have exactly 3 components (major.minor.patch)
    if len(version_parts) != 3:
        get_effective_logger().warning(
            f"trackme_schema_format_version: invalid version format '{trackme_version}' "
            f"(expected major.minor.patch format). Returning 0 to assume schema is up to date."
        )
        return 0
    
    try:
        major, minor, patch = version_parts

        # Ensure the patch version is two digits
        patch = patch.zfill(2)

        # Combine the parts and convert to integer
        schema_version_required = int(major + minor + patch)

        return schema_version_required
    except (ValueError, AttributeError) as e:
        get_effective_logger().warning(
            f"trackme_schema_format_version: error parsing version '{trackme_version}': {str(e)}. "
            "Returning 0 to assume schema is up to date."
        )
        return 0


# update the schema version to a certain release number
def trackme_schema_get_version(
    reqinfo, tenant_id, schema_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_get_version, tenant_id="{tenant_id}"'
    )

    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, trackme_schema_get_version, the vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, trackme_schema_get_version, the vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # try to get the schema version
        try:
            tenant_schema_version = vtenant_record.get("schema_version")
        except Exception as e:
            tenant_schema_version = None

        # update as needed
        if not tenant_schema_version:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", trackme_schema_get_version, this tenant does not have a schema version defined yet, processing now.'
            )
            return None
        else:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", trackme_schema_get_version, current schema_version="{tenant_schema_version}"'
            )
            return tenant_schema_version


# update the schema version to a certain release number
def trackme_schema_update_version(
    reqinfo, tenant_id, schema_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().debug(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_update_version, tenant_id="{tenant_id}"'
    )

    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # try to get the schema version
        try:
            tenant_schema_version = vtenant_record.get("schema_version")
        except Exception as e:
            tenant_schema_version = None

        # logging debug
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", current schema_version="{tenant_schema_version}"'
        )

        # update as needed
        if not tenant_schema_version:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema version check, this tenant does not have a schema version defined yet, processing its update now.'
            )

            try:
                vtenant_record["schema_version"] = schema_version
                vtenant_record["schema_version_mtime"] = time.time()
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema version upgraded successfully, new schema_version="{schema_version}"'
                )
                return {
                    "action": "success",
                    "response": "schema version was successfully upgraded",
                    "schema_version": schema_version,
                }

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )
                raise Exception(
                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )

        elif tenant_schema_version != schema_version:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema version check, this tenant needs to be upgraded, current_schema_version="{tenant_schema_version}", target_schema_version="{schema_version}", processing its update now.'
            )

            try:
                vtenant_record["schema_version"] = schema_version
                vtenant_record["schema_version_mtime"] = time.time()
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema version upgraded successfully, new schema_version="{schema_version}"'
                )
                return {
                    "action": "success",
                    "response": "schema version was successfully upgraded",
                    "schema_version": schema_version,
                }

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )
                raise Exception(
                    f'failure while trying to update the vtenant KVstore record, exception="{str(e)}"'
                )

        else:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema version check, this tenant schema is up to date, nothing to do.'
            )
            return {
                "action": "success",
                "schema_version": schema_version,
            }


# get permissions
def get_permissions(vtenant_record):

    # for read permissions, concatenate admin, power and user
    tenant_roles_read_perms = f"{vtenant_record.get('tenant_roles_admin', 'trackme_admin')},{vtenant_record.get('tenant_roles_power', 'trackme_power')},{vtenant_record.get('tenant_roles_user', 'trackme_user')}"

    # for write permissions, concatenate admin, power
    tenant_roles_write_perms = f"{vtenant_record.get('tenant_roles_admin', 'trackme_admin')},{vtenant_record.get('tenant_roles_power', 'trackme_power')}"

    return tenant_roles_read_perms, tenant_roles_write_perms


def update_vtenant_configuration(
    reqinfo, task_name, task_instance_id, tenant_id, updated_vtenant_data=None
):
    """
    Update the configuration of a vtenant by first fetching the current configuration,
    merging with default values, and applying any updates. If a dict of key-value
    pairs is provided, it takes precedence over the defaults.
    Any key from the GET response not in the default config should be kept.

    :param reqinfo: dict containing Splunk session information (e.g., server URI, session key).
    :param task_name: Name of the task for logging purposes.
    :param task_instance_id: ID of the task instance for logging purposes.
    :param tenant_id: ID of the vtenant.
    :param updated_vtenant_data: Optional dict containing key-value pairs to update in the vtenant configuration.
    """

    # endpoint target
    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/maintain_vtenant_account'

    # post data
    post_data = {
        "tenant_id": tenant_id,
        "force_create_missing": True,
    }

    # add updated_vtenant_data if provided
    if updated_vtenant_data:
        post_data["updated_vtenant_data"] = updated_vtenant_data

    try:
        # Get current vtenant account configuration
        response = requests.post(
            url,
            headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
            verify=False,
            data=json.dumps(post_data),
            timeout=600,
        )

        if response.status_code in (200, 201, 204):
            response_json = response.json()
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, successfully call vtenant check and maintain endpoint, response="{json.dumps(response_json, indent=2)}"'
            )
            return True

        else:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, failed to retrieve vtenant configuration, status_code={response.status_code}'
            )
            return False

    except Exception as e:
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, error while fetching vtenant configuration: {str(e)}'
        )
        return False


def update_remote_account_configuration(
    reqinfo, task_name, task_instance_id, tenant_id, default_account_values=None
):
    """
    Update the configuration of any existing remote account, to ensure that the configuration is up to date.

    :param reqinfo: dict containing Splunk session information (e.g., server URI, session key).
    :param task_name: Name of the task for logging purposes.
    :param task_instance_id: ID of the task instance for logging purposes.
    :param tenant_id: ID of the vtenant.
    :param default_account_values: manadatory dict of default values.
    """

    # endpoint target
    url = f'{reqinfo["server_rest_uri"]}/servicesNS/nobody/trackme/trackme_account'

    # current_remote_accounts_dict
    current_remote_accounts_dict = {}

    # first, get the list of remote accounts
    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f'Splunk {reqinfo["session_key"]}',
                "Content-Type": "application/json",
            },
            verify=False,
            params={
                "output_mode": "json",
                "count": -1,
            },
            timeout=600,
        )

        response.raise_for_status()
        response_json = response.json()

        # The list of remote accounts is stored as a list in entry
        remote_accounts = response_json.get("entry", [])

        # iterate through the remote accounts, adding them to the dict, name is the key, then we care about "content" which is a dict of our parameters
        # for this account

        for remote_account in remote_accounts:
            remote_account_name = remote_account.get("name", None)
            remote_account_content = remote_account.get("content", {})

            if remote_account_name and remote_account_content:

                # from remote_account_content, remove the following fields: bearer_token, disabled, eai:acl, eai:appName, eai:userName
                remote_account_content.pop("bearer_token", None)
                remote_account_content.pop("disabled", None)
                remote_account_content.pop("eai:acl", None)
                remote_account_content.pop("eai:appName", None)
                remote_account_content.pop("eai:userName", None)
                # add to the dict
                current_remote_accounts_dict[remote_account_name] = (
                    remote_account_content
                )

    except Exception as e:
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", task="{task_name}", task_instance_id={task_instance_id}, error while fetching remote account list: {str(e)}'
        )
        return False

    # Second, iterate through our current_remote_accounts_dict, if any of the account is missing key/values from the default_account_values, we will update it
    # running a POST request to the remote account endpoint

    for remote_account_name in current_remote_accounts_dict:
        current_account_config = current_remote_accounts_dict[remote_account_name]

        # check if the account is missing any key/values from the default_account_values
        account_must_be_updated = False
        for key in default_account_values:
            if key not in current_account_config:
                account_must_be_updated = True
                # update the current_account_config with the default value
                current_account_config[key] = default_account_values[key]

                # run a request against /services/trackme/v2/configuration/get_remote_account, body{'account': 'prd1_cm1'} to retrieve the current bearer_token value (field token) and add to the content
                try:
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/get_remote_account'
                    data = {
                        "account": remote_account_name,
                    }
                    response_account_secret = requests.post(
                        url,
                        headers={
                            "Authorization": f'Splunk {reqinfo["session_key"]}',
                            "Content-Type": "application/json",
                        },
                        verify=False,
                        data=json.dumps(data),
                        timeout=600,
                    )
                    response_account_secret.raise_for_status()
                    response_account_secret_json = response_account_secret.json()
                    current_token = response_account_secret_json.get("token", None)

                    if not current_token:
                        get_effective_logger().error(
                            f'tenant_id="{tenant_id}", task="{task_name}", task_instance_id={task_instance_id}, account={remote_account_name}, error while fetching remote account secret: token not found'
                        )
                        account_must_be_updated = False

                    else:
                        current_account_config["bearer_token"] = current_token

                except Exception as e:
                    get_effective_logger().error(
                        f'tenant_id="{tenant_id}", task="{task_name}", task_instance_id={task_instance_id}, account={remote_account_name}, error while fetching remote account secret: {str(e)}'
                    )
                    account_must_be_updated = False

        # if the account must be updated, we will run a POST request to the remote account endpoint
        if account_must_be_updated:
            # endpoint target
            url = f'{reqinfo["server_rest_uri"]}/servicesNS/nobody/trackme/trackme_account/{remote_account_name}?output_mode=json'

            try:
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f'Splunk {reqinfo["session_key"]}',
                        "Content-Type": "application/json",
                    },
                    verify=False,
                    params=current_account_config,
                    timeout=600,
                )
                response.raise_for_status()
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", task="{task_name}", task_instance_id={task_instance_id}, successfully updated remote account configuration for missing default values, account={remote_account_name}, status={response.status_code}'
                )

            except Exception as e:
                get_effective_logger().error(
                    f'tenant_id="{tenant_id}", task="{task_name}", task_instance_id={task_instance_id}, error while updating remote account configuration: {str(e)}'
                )
                return False

    return True


# process update version 2.0.9
# changes: in version 2.0.9, we introduced a new Ack Metadata, ack_type, which requires an update of the KV transform


def trackme_schema_upgrade_2009(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2009, tenant_id="{tenant_id}"'
    )

    # dict of collections
    collections_dict = dict(
        [
            (
                "trackme_common_alerts_ack",
                "_key, object, object_category, ack_mtime, ack_expiration, ack_state, ack_type, ack_comment",
            ),
        ]
    )

    # name of the object
    object_name = "trackme_common_alerts_ack"

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        transform_name = "trackme_common_alerts_ack_tenant_" + str(tenant_id)
        collection_name = "kv_trackme_common_alerts_ack_tenant_" + str(tenant_id)
        transform_fields = collections_dict[object_name]
        transform_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": "app",
            "perms.write": vtenant_record.get("tenant_roles_admin"),
            "perms.read": vtenant_record.get("tenant_roles_user"),
        }

        # delete the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        # create the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
            "transform_fields": transform_fields,
            "collection_name": collection_name,
            "transform_acl": transform_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 209, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2015(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2015, tenant_id="{tenant_id}"'
    )

    # dict of collections
    collections_dict = dict(
        [
            (
                "trackme_dsm",
                "_key, mtime, search_mode, tenant_id, object_category, alias, data_index, data_last_lag_seen, data_last_ingestion_lag_seen, data_eventcount, data_last_lag_seen_idx, data_first_time_seen, data_last_time_seen, data_last_ingest, data_last_time_seen_idx, data_max_lag_allowed, data_max_delay_allowed, monitored_state, object, data_sourcetype, data_monitoring_wdays, isUnderMonitoringDays, data_monitoring_hours_ranges, isUnderMonitoringHours, data_override_lagging_class, object_state, tracker_runtime, object_previous_state, data_previous_tracker_runtime, dcount_host, min_dcount_host, isAnomaly, data_sample_lastrun, tags, latest_flip_state, latest_flip_time, priority, status_message, anomaly_reason",
            ),
            (
                "trackme_flx",
                "_key, mtime, tenant_id, group, object, object_category, object_state, object_description, alias, monitored_state, account, tracker_name, tracker_runtime, status, status_description, metrics, outliers_metrics, monitoring_wdays, isUnderMonitoringDays, monitoring_hours_ranges, isUnderMonitoringHours, latest_flip_state, latest_flip_time, priority, status_message, anomaly_reason",
            ),
            (
                "trackme_dhm",
                "_key, mtime, search_mode, tenant_id, object_category, object, alias, data_index, data_sourcetype, data_last_lag_seen, data_last_ingestion_lag_seen, data_eventcount, data_first_time_seen, data_last_time_seen, data_last_ingest, data_max_lag_allowed, data_max_delay_allowed, monitored_state, data_monitoring_wdays, isUnderMonitoringDays, data_monitoring_hours_ranges, isUnderMonitoringHours, data_override_lagging_class, object_state, tracker_runtime, object_previous_state, data_previous_tracker_runtime, splk_dhm_st_summary, splk_dhm_alerting_policy, latest_flip_state, latest_flip_time, priority, status_message, anomaly_reason",
            ),
            (
                "trackme_mhm",
                "_key, mtime, tenant_id, object_category, object, alias, metric_index, metric_category, metric_details, metric_last_lag_seen, metric_first_time_seen, metric_last_time_seen, metric_max_lag_allowed, monitored_state, metric_monitoring_wdays, metric_override_lagging_class, object_state, tracker_runtime, object_previous_state, metric_previous_tracker_runtime, latest_flip_state, latest_flip_time, priority, status_message, anomaly_reason",
            ),
        ]
    )

    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("trackme_mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx")

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": vtenant_record.get("tenant_roles_user"),
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2015, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2016(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2016, tenant_id="{tenant_id}"'
    )

    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append(
                "trackme_dsm_outliers_mltrain_tracker_tenant_%s" % tenant_id
            )

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append(
                "trackme_dhm_outliers_mltrain_tracker_tenant_%s" % tenant_id
            )

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append(
                "trackme_flx_outliers_mltrain_tracker_tenant_%s" % tenant_id
            )

        for report_name in objects_to_process:
            # create the report
            component = None

            if report_name.startswith("trackme_dsm"):
                component = "dsm"
            elif report_name.startswith("trackme_dhm"):
                component = "dhm"
            elif report_name.startswith("trackme_flx"):
                component = "flx"

            report_search = (
                '| trackmesplkoutlierstrainhelper tenant_id="%s" component="%s"'
                % (tenant_id, component)
            )
            report_properties = {
                "description": "This scheduled report generate and trains Machine Learning models for the tenant",
                "is_scheduled": True,
                "cron_schedule": "0 22-23,0-6 * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # for read permissions, concatenate admin and guest
            tenant_roles_read_perms = "%s,%s" % (
                str(vtenant_record.get("tenant_roles_admin")),
                str(vtenant_record.get("tenant_roles_user")),
            )

            # delete the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", delete report has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted report, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the report, report="{report_name}", exception="{str(e)}"'
                )

            # create the report
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2016, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2020(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # not if target_version > 2064
    if target_version > 2064:
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2020, procedure terminated, target_version="{target_version}"'
        )
        return True

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2020, tenant_id="{tenant_id}"'
    )

    components_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")

        # loop
        for component in components_to_process:
            # for read permissions, concatenate admin and guest
            tenant_roles_read_perms = "%s,%s" % (
                str(vtenant_record.get("tenant_roles_admin")),
                str(vtenant_record.get("tenant_roles_user")),
            )

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the wrapper
            report_name = (
                f"trackme_{component}_delayed_entities_tracker_tenant_{tenant_id}"
            )
            if component in ("dsm"):
                report_search = f'| trackmesplkfeedsdelayed tenant_id="{tenant_id}" component="{component}" earliest="-24h" latest="+4h" max_runtime_sec="3600" max_ingest_age_sec="86400" min_time_since_inspection_sec="900" dsm_tstats_root_breakby_include_splunk_server=True dsm_tstats_root_breakby_include_host=True'
            elif component in ("dhm"):
                report_search = f'| trackmesplkfeedsdelayed tenant_id="{tenant_id}" component="{component}" earliest="-24h" latest="+4h" max_runtime_sec="3600" max_ingest_age_sec="86400" min_time_since_inspection_sec="900" dhm_tstats_root_breakby_include_splunk_server=True'
            report_properties = {
                "description": "This scheduled report handled delayed entities for the tenant and component",
                "is_scheduled": True,
                "cron_schedule": "*/60 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2020, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2026(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2026, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # init the wlk component to be disabled
        vtenant_record["tenant_wlk_enabled"] = 0

        # update
        try:
            collection_vtenants.data.update(
                str(vtenant_key), json.dumps(vtenant_record)
            )
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2026, Virtual Tenant updated successfully, result="{json.dumps(vtenant_record, indent=2)}"'
            )

        except Exception as e:
            error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, function trackme_schema_upgrade_2026, failed to update the Virtual Tenant record, exception="{str(e)}"'
            get_effective_logger().error(error_msg)

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2026, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2034(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2034, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # first, introduce the tenant_replica boolean and update the tenant record
        vtenant_record["tenant_replica"] = False
        try:
            collection_vtenants.data.update(
                str(vtenant_key), json.dumps(vtenant_record)
            )
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, vtenant record was updated successfully, tenant_replica was set to False'
            )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, vtenant record update has failed, tenant_replica has not been set, exception="{str(e)}"'
            )

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("trackme_mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk")

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": vtenant_record.get("tenant_roles_user"),
            }

            # proceed boolean
            proceed = False

            # check first if the transforms exists, if it does not exist, we do not need to proceed
            try:
                transform__current = service.confs["transform_name"]
                proceed = True
            except Exception as e:
                proceed = False
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", transform does not exist, no need to proceed, transform="{transform_name}"'
                )

            if proceed:

                # delete the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": transform_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        # log
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, function trackme_schema_upgrade_2034 terminated, tenant_id="{tenant_id}"'
        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2034, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2034_least_privileges(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2034_least_privileges, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # get the admin value
        try:
            current_tenant_roles_admin = vtenant_record["tenant_roles_admin"]
        except Exception as e:
            current_tenant_roles_admin = "trackme_admin"

        # set a value
        tenant_roles_power = None
        if current_tenant_roles_admin != "trackme_admin":
            tenant_roles_power = current_tenant_roles_admin
        else:
            tenant_roles_power = "trackme_power"

        # update the record
        vtenant_record["tenant_roles_power"] = tenant_roles_power

        # update
        try:
            collection_vtenants.data.update(
                str(vtenant_key), json.dumps(vtenant_record)
            )
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2034 (least privileges), Virtual Tenant updated successfully, result="{json.dumps(vtenant_record, indent=2)}"'
            )

        except Exception as e:
            error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, function trackme_schema_upgrade_2034_leat_privileges, failed to update the Virtual Tenant record, exception="{str(e)}"'
            get_effective_logger().error(error_msg)

        # RBAC update

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % reqinfo["session_key"],
            "Content-Type": "application/json",
        }

        url = "%s/services/trackme/v2/vtenants/admin/update_tenant_rbac" % (
            reqinfo["server_rest_uri"]
        )
        data = {
            "tenant_id": tenant_id,
            "tenant_roles_admin": vtenant_record["tenant_roles_admin"],
            "tenant_roles_power": vtenant_record["tenant_roles_power"],
            "tenant_roles_user": vtenant_record["tenant_roles_user"],
            "tenant_owner": vtenant_record["tenant_owner"],
        }

        # create the account
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2034 (least privileges), RBAC update has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2034 (least privileges), RBAC update was operated successfully, response="{json.dumps(response.json(), indent=2)}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2034 (least privileges), RBAC update has failed, exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2034, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2036(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2036, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        # proceed boolean
        proceed = False

        # First, run a get request to check the vtenant account exists already, if not, create it
        url = f'{reqinfo["server_rest_uri"]}/servicesNS/nobody/trackme/trackme_vtenants/{vtenant_record.get("tenant_id")}'
        try:
            response = requests.get(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                verify=False,
                timeout=600,
            )
            if response.status_code in (200, 201, 204):
                proceed = False
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, vtenant account already exists, tenant_id="{tenant_id}"'
                )
            else:
                proceed = True
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, vtenant account does not exist, tenant_id="{tenant_id}"'
                )
        except Exception as e:
            proceed = True
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, failed to check the vtenant account, exception="{str(e)}"'
            )

        if proceed:

            #
            # Create the vtenant account configuration
            #

            url = f'{reqinfo["server_rest_uri"]}/servicesNS/nobody/trackme/trackme_vtenants'
            data = {
                "name": vtenant_record.get("tenant_id"),
                "description": vtenant_record.get("tenant_desc"),
            }

            # add to data each key value from vtenant_account_default imported
            for key, value in vtenant_account_default.items():
                data[key] = value

            # create the account
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=data,
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, create vtenant account has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, create vtenant account was operated successfully, response.status_code="{response.status_code}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, create vtenant account has failed, exception="{str(e)}"'
                )

        #
        # Decomission of the data sampling obfuscation macro
        #

        if vtenant_record.get("tenant_dsm_enabled") == 1:

            # proceed boolean
            proceed = False

            # get permissions
            tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
                vtenant_record
            )

            # deletion of the sampling tracker
            report_name = f"trackme_dsm_data_sampling_tracker_tenant_{tenant_id}"

            # First, check if the report exists, it is does we have nothing to do
            try:
                report_current = service.saved_searches[report_name]
                proceed = True
            except Exception as e:
                proceed = False
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, report does not exist, nothing to do, report="{report_name}"'
                )

            if proceed:

                # delete the report
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", delete report has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", successfully deleted report, report="{report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", failed to delete the report, report="{report_name}", exception="{str(e)}"'
                    )

            # attempt to create the new fresh tracker
            # trackme-limited/trackme-report-issues#839: the schema upgrade will fail to create the report as macros originally called do not exist anymore.
            # This restricted version will address this issue.
            report_search = f'| trackmesamplingexecutor tenant_id="{tenant_id}"'
            report_properties = {
                "description": "TrackMe DSM Data Sampling tracker",
                "is_scheduled": True,
                "schedule_window": "5",
                "cron_schedule": "*/20 22-23,0-6 * * *",
                "dispatch.earliest_time": "-24h",
                "dispatch.latest_time": "-4h",
            }

            report_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": str(tenant_roles_write_perms),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

            # decomission the macro
            macro_name = f"trackme_dsm_data_sampling_obfuscation_tenant_{tenant_id}"

            # delete the macro
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_macro'
            data = {
                "tenant_id": tenant_id,
                "macro_name": macro_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", delete macro has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", successfully deleted macrp, macro="{macro_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", failed to delete the report, macro="{macro_name}", exception="{str(e)}"'
                )

        #
        # Replica tenant
        #

        # then, introduce the tenant_replica boolean and update the tenant record
        vtenant_record["tenant_replica"] = False
        try:
            collection_vtenants.data.update(
                str(vtenant_key), json.dumps(vtenant_record)
            )
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, vtenant record was updated successfully, tenant_replica was set to False'
            )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, vtenant record update has failed, tenant_replica has not been set, exception="{str(e)}"'
            )

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("trackme_mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk")

        for object_name in objects_to_process:
            transform_name = f"{object_name}_tenant_{tenant_id}"
            collection_name = f"kv_{object_name}_tenant_{tenant_id}"
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": vtenant_record.get("tenant_roles_user"),
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2036, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2036, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2038(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2038, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("trackme_mhm")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2038, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2043(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2043, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm_outliers_entity_rules")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm_outliers_entity_rules")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx_outliers_entity_rules")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk_outliers_entity_rules")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2043, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2044(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2044, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2044, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2045(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2045, tenant_id="{tenant_id}"'
    )

    components_to_process = []
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        # check components and add accordingly
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
            objects_to_process.append("trackme_flx")

        #
        # objects
        #

        for object_name in objects_to_process:

            # get permissions
            tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
                vtenant_record
            )

            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # components
        #

        for component in components_to_process:

            # get permissions
            tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
                vtenant_record
            )

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the wrapper
            report_name = (
                f"trackme_{component}_inactive_entities_tracker_tenant_{tenant_id}"
            )
            report_search = f'| trackmesplkflxinactiveinspector tenant_id="{tenant_id}" register_component="True" report="{report_name}" max_sec_since_inactivity_before_status_update=3600 max_days_since_inactivity_before_purge=7'
            report_properties = {
                "description": "This scheduled report handles inactive entities for the splk-flx component",
                "is_scheduled": True,
                "cron_schedule": "*/15 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2045, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2054(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2054, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2054, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2064(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Access the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Access the dedicated exec summary collection
    collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
    collection_exec_summary = service.kvstore[collection_exec_summary_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2064, tenant_id="{tenant_id}"'
    )

    components_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")

        # Retrieve the exec summary record from the dedicated collection
        try:
            exec_summary_records = collection_exec_summary.data.query(query=json.dumps(query_string))
            if exec_summary_records:
                exec_summary_record = exec_summary_records[0]
                exec_summary_key = exec_summary_record.get("_key")
            else:
                exec_summary_record = None
                exec_summary_key = None
        except Exception as e:
            exec_summary_record = None
            exec_summary_key = None

        # load tenant_objects_exec_summary as an object
        try:
            tenant_objects_exec_summary = json.loads(
                exec_summary_record.get("tenant_objects_exec_summary")
            ) if exec_summary_record else {}
        except Exception as e:
            tenant_objects_exec_summary = {}

        # results
        results = []

        # loop
        for component in components_to_process:

            # proceed boolean
            proceed = False

            # create the wrapper
            report_name = (
                f"trackme_{component}_delayed_entities_tracker_tenant_{tenant_id}"
            )

            # only proceed if the report exists
            try:
                report_obj = service.saved_searches[report_name]
                proceed = True
            except Exception as e:
                proceed = False

            if proceed:

                # delete the report
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", delete report has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted report, report="{report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the report, report="{report_name}", exception="{str(e)}"'
                    )

                # attempt to clear the tenant_objects_exec_summary record from this object
                try:
                    tenant_objects_exec_summary.pop(report_name)
                    exec_summary_data = {
                        "tenant_id": tenant_id,
                        "tenant_objects_exec_summary": json.dumps(
                            tenant_objects_exec_summary, indent=2
                        ),
                    }
                    if exec_summary_key:
                        collection_exec_summary.data.update(
                            str(exec_summary_key), json.dumps(exec_summary_data)
                        )
                    else:
                        collection_exec_summary.data.insert(json.dumps(exec_summary_data))
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully cleared the tenant_objects_exec_summary record, report="{report_name}"'
                    )
                    results.append(
                        f'tenant_id="{tenant_id}", successfully cleared the tenant_objects_exec_summary record, report="{report_name}"'
                    )
                except Exception as e:
                    pass

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2064, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2067(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2067, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        # check components and add accordingly
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            process_schema_upgrade = True
        else:
            process_schema_upgrade = False

        if process_schema_upgrade:
            # Define the query
            search = f'| inputlookup trackme_wlk_tenant_{tenant_id} | eval key = _key | where match(object, "\\\\\\\\") | table key, object'

            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # A list to store all executions
            results_list = []

            # A dict to store the results
            results_dict = {}

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
                        results_dict[item["key"]] = item["object"]
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", detected non ASCII entity to be purged, object="{item["object"]}", key="{item["key"]}"'
                        )

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", could not verify the presence of non ASCII entities, search permanently failed, exception="{str(e)}"'
                )

            # if the results_dict is not empty, we need to purge the entities
            if results_dict:
                # Data collection
                collection_name = "kv_trackme_wlk_tenant_" + str(tenant_id)
                collection = service.kvstore[collection_name]

                # loop through the results dict and remove any entity from the KVstore
                for key, object in results_dict.items():
                    try:
                        collection.data.delete(json.dumps({"_key": key}))
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", successfully purged non ASCII entity, object="{object}", key="{key}"'
                        )
                        results_list.append(
                            {
                                "object": object,
                                "key": key,
                                "result": "successfully purged non ASCII entity",
                            }
                        )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", failed to purge non ASCII entity, object="{object}", key="{key}", exception="{str(e)}"'
                        )
                        results_list.append(
                            {
                                "object": object,
                                "key": key,
                                "result": "failure to purge non ASCII entity",
                                "exception": str(e),
                            }
                        )

            # log a message if there were no entities to be purged
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", no non ASCII entities to be purged'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2067, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2070(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2070, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2070, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2071(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2071, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", processing with the schema upgrade'
            )

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_dict = {}

            trackers_to_process = []
            trackers_to_process_kos = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:
                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = tracker_record.get("knowledge_objects")

                # if the tracker_name starts by scheduler_
                if re.search("^scheduler_", tracker_name):
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)

                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

            # loop through the trackers
            for tracker_shortname in trackers_to_process:
                tracker_name = (
                    f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"
                )

                tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_account = tracker_kos["properties"][0]["account"]

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                )

                # in tracker_current_search, replace the sentence:
                # | fields - collection_app, collection_user
                # with: (note that account need to replaced by the actual account name)
                # | fields - collection_app, collection_user
                # ``` Verify the report owner from rest if it is not yet known to TrackMe ```
                # | trackmesplkwlkgetreportowner account="{account}"

                try:
                    tracker_new_search = re.sub(
                        r"\| fields - collection_app, collection_user",
                        f'| fields - collection_app, collection_user\n\n``` Verify the report owner from rest if it is not yet known to TrackMe, this custom command will perform a get Metadata operation attempt if necessary ```\n| trackmesplkwlkgetreportowner account="{tracker_account}"\n',
                        tracker_current_search,
                    )

                    # update the search definition
                    tracker_current.update(search=tracker_new_search)

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, the tracker was updated successfully, new_search="{tracker_new_search}"'
                    )

                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, failed to update the tracker, exception="{str(e)}"'
                    )

        # check components and add accordingly
        objects_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2071, procedure terminated'
    )
    return True


"""
In this function:
- A bug had affected the definition of outliers rules for wlk, activating lower bound breaches for elapsed which is unwanted
- Enhance the scheduler execution errors detection by taking into account searches in delegated errors
- Update transforms for dsm/dhm for the purposes of allow_adaptive_delay
- Update ML Outliers rules transforms to add the confidence and confidence_reason fields
- Initialize ML Outliers values for confidence and confidence_reason
"""


def trackme_schema_upgrade_2072(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2072, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        #
        # prepare transforms updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # main transforms updates
        #

        # check components and add accordingly
        objects_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # ML rules outliers transforms update
        #

        # check components and add accordingly
        objects_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm_outliers_entity_rules")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm_outliers_entity_rules")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx_outliers_entity_rules")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk_outliers_entity_rules")

        for object_name in objects_to_process:
            transform_name = f"{object_name}_tenant_{tenant_id}"
            collection_name = f"kv_{object_name}_tenant_{tenant_id}"
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # ML: initiate confidence and confidence_reason fields for existing tenants
        #

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        # Get the value for splk_outliers_min_days_history
        splk_outliers_min_days_history = reqinfo["trackme_conf"][
            "splk_outliers_detection"
        ]["splk_outliers_min_days_history"]

        # resolve the metric index for this tenant (once, before the loop)
        tenant_indexes = trackme_idx_for_tenant(
            reqinfo["session_key"],
            reqinfo["server_rest_uri"],
            tenant_id,
        )
        tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

        for component in components_to_process:
            # set kwargs
            kwargs_confidence = {
                "earliest_time": "-90d",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # define the gen search
            metric_root = None
            if component in ("dsm", "dhm"):
                metric_root = f"trackme.splk.feeds"
            else:
                metric_root = f"trackme.splk.{component}"

            ml_confidence_search = remove_leading_spaces(
                f"""\
                | mstats latest({metric_root}.*) as * where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object=* by object span=1d
                | stats min(_time) as first_time by object
                | eval metrics_duration=now()-first_time
                | eval days_required = {splk_outliers_min_days_history}
                | eval confidence=if(metrics_duration<(days_required*86400), "low", "normal")
                | eval metrics_duration=tostring(metrics_duration, "duration")
                | eval confidence_reason=if(metrics_duration<(days_required*86400), "ML has insufficient historical metrics to proceed (metrics_duration=" . metrics_duration . ", required=" . days_required + "days)", "ML has sufficient historical metrics to proceed (metrics_duration=" . metrics_duration . ", required=" . days_required . "days)")
                | fields object, confidence, confidence_reason
                | lookup local=t trackme_{component}_outliers_entity_rules_tenant_{tenant_id} object OUTPUT _key as keyid, entities_outliers, is_disabled, last_exec, mtime, object_category | where (isnotnull(keyid) AND isnotnull(confidence))
                | outputlookup append=t key_field=keyid trackme_{component}_outliers_entity_rules_tenant_{tenant_id}
                """
            )

            ml_confidence_update_counter = 0
            ml_confidence_updated_entities = []

            # run search

            # track the search runtime
            start = time.time()

            # proceed
            try:
                reader = run_splunk_search(
                    service,
                    ml_confidence_search,
                    kwargs_confidence,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        ml_confidence_update_counter += 1
                        ml_confidence_updated_entities.append(item.get("object"))

            except Exception as e:
                msg = (
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", '
                    f'search failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
                )
                get_effective_logger().error(msg)

            # log
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", ml_confidence_update_counter="{ml_confidence_update_counter}", ml_confidence_updated_entities="{json.dumps(ml_confidence_updated_entities, indent=2)}"'
            )

        #
        # Adaptive delay tracker
        #

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Create the adaptive delay tracker
            #

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": trackme_default_sharing,
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the wrapper
            report_name = (
                f"trackme_{component}_adaptive_delay_tracker_tenant_{tenant_id}"
            )
            report_search = f'| trackmesplkadaptivedelay tenant_id="{tenant_id}" component="{component}" min_delay_sec=3600 min_historical_metrics_days=7 earliest_time_mstats="-30d" max_runtime=900'
            report_properties = {
                "description": "This scheduled report manages adaptive delay thresholds for TrackMe",
                "is_scheduled": True,
                "cron_schedule": "*/15 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

        #
        # Variable delay review tracker
        #

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Create the variable delay review tracker
            #

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": trackme_default_sharing,
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the wrapper
            report_name = (
                f"trackme_{component}_variable_delay_review_tracker_tenant_{tenant_id}"
            )
            report_search = f'| trackmesplkvariabledelayreview tenant_id="{tenant_id}" component="{component}" review_frequency_sec=604800 deviation_threshold_pct=20 lookback="-30d" method="perc95" min_samples=10 max_threshold_sec=604800 max_runtime=7200'
            report_properties = {
                "description": "This scheduled report manages variable delay auto-review for TrackMe",
                "is_scheduled": True,
                "cron_schedule": "30 2 * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

        #
        # Workload
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", processing with the schema upgrade'
            )

            #
            # fix outliers rules
            #

            # access the KV
            collection_outliers_rules_name = (
                f"kv_trackme_wlk_outliers_entity_rules_tenant_{tenant_id}"
            )
            collection_outliers_rules = service.kvstore[collection_outliers_rules_name]

            # get all records
            collection_records = []
            collection_records_keys = set()

            end = False
            skip_tracker = 0
            while end == False:
                process_collection_records = collection_outliers_rules.data.query(
                    skip=skip_tracker
                )
                if len(process_collection_records) != 0:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            # loop through the records
            for outlier_record in collection_records:
                entities_outliers = json.loads(outlier_record.get("entities_outliers"))
                for model_id in entities_outliers:
                    kpi_metric = entities_outliers[model_id].get("kpi_metric")
                    if kpi_metric == "splk.wlk.elapsed":
                        entities_outliers[model_id]["alert_lower_breached"] = 0

                # update the record
                outlier_record["entities_outliers"] = json.dumps(
                    entities_outliers, indent=2
                )

                # update the KVstore
                try:
                    collection_outliers_rules.data.update(
                        outlier_record.get("_key"),
                        json.dumps(outlier_record, indent=2),
                    )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the entity rules, exception="{str(e)}"'
                    )

            #
            # enhance scheduler execution errors detection
            #

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_dict = {}

            trackers_to_process = []
            trackers_to_process_kos = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:
                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = tracker_record.get("knowledge_objects")

                # if the tracker_name starts by scheduler_
                if re.search("^scheduler_", tracker_name):
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)

                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

            # loop through the trackers
            for tracker_shortname in trackers_to_process:
                tracker_name = (
                    f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"
                )

                tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_account = tracker_kos["properties"][0]["account"]

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                )

                # in tracker_current_search, replace the sentence:
                # len(errmsg)>0,\"error\"
                # with: (note that account need to replaced by the actual account name)
                # len(errmsg)>0,\"error\" OR status == \"delegated_remote_error\"

                if tracker_account == "local":
                    tracker_new_search = re.sub(
                        r'len\(errmsg\)>0,"error"',
                        r'len(errmsg)>0 OR status == "delegated_remote_error","error"',
                        tracker_current_search,
                    )
                else:
                    tracker_new_search = re.sub(
                        r'len\(errmsg\)>0,\\"error\\"',
                        r'len(errmsg)>0 OR status == \\"delegated_remote_error\\",\\"error\\"',
                        tracker_current_search,
                    )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

            #
            # Update the metadata search to include an explicit call to filters_get_last_updates="host=*"
            #

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_dict = {}

            trackers_to_process = []
            trackers_to_process_kos = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:
                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = tracker_record.get("knowledge_objects")

                # if the tracker_name starts by scheduler_
                if re.search("^metadata_", tracker_name):
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)

                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

            # loop through the trackers
            for tracker_shortname in trackers_to_process:
                tracker_name = (
                    f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"
                )

                tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_account = tracker_kos["properties"][0]["account"]

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                )

                # in tracker_current_search, replace the sentence:
                # max_runtime_sec="900"
                # with:
                # max_runtime_sec="900" filters_get_last_updates="host=*"

                tracker_new_search = re.sub(
                    r'max_runtime_sec="900"',
                    r'max_runtime_sec="900" filters_get_last_updates="host=*"',
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

            #
            # ML Outliers: update the default Outliers rules macro
            #

            macro_name = f"trackme_wlk_set_outliers_metrics_tenant_{tenant_id}"
            macro_current = service.confs["macros"][macro_name]
            macro_current_definition = macro_current.content.get("definition")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", macro_name="{macro_name}", macro_current_definition="{macro_current_definition}", processing macro update'
            )

            """
            In macro_current_defintion, replace:
            
            eval outliers_metrics="{'elapsed': {'alert_lower_breached': 0, 'alert_upper_breached': 1}}"
            
            by:
            
            eval outliers_metrics="{'elapsed': {'alert_lower_breached': 0, 'alert_upper_breached': 1, 'time_factor': 'none'}}"

            """

            macro_new_definition = "eval outliers_metrics=\"{'elapsed': {'alert_lower_breached': 0, 'alert_upper_breached': 1, 'time_factor': 'none'}}\""

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_macro'
            data = {
                "tenant_id": tenant_id,
                "macro_name": macro_name,
                "macro_definition": macro_new_definition,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update macro definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated macro definition, transform="{macro_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the macro definition, transform="{macro_name}", exception="{str(e)}"'
                )

            #
            # ML Outliers: mass update rules for wlk
            #

            # set kwargs
            kwargs_wlk_outliers_rules_update = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # define the gen search
            wlk_outliers_rules_update_search = remove_leading_spaces(
                f"""\
                | inputlookup trackme_wlk_outliers_entity_rules_tenant_{tenant_id} | eval keyid=_key
                ``` mass update the time_factor ```
                | rex field=entities_outliers mode=sed "s/\\\"time_factor\\\": \\\"%H\\\"/\\\"time_factor\\\": \\\"none\\\"/g"
                ``` force update the confidence and confidence_reason ```
                | eval confidence="low", confidence_reason="upgrade to TrackMe 2.0.72 for splk-wlk requires models to be trained again due to the change of the time_factor field, which will happen automatically as soon as possible."
                | outputlookup append=t key_field=keyid trackme_wlk_outliers_entity_rules_tenant_{tenant_id}
                """
            )

            wlk_outliers_rules_update_counter = 0
            wlk_outliers_rules_updated_entities = []

            # run search

            # track the search runtime
            start = time.time()

            # proceed
            try:
                reader = run_splunk_search(
                    service,
                    wlk_outliers_rules_update_search,
                    kwargs_wlk_outliers_rules_update,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        wlk_outliers_rules_update_counter += 1
                        wlk_outliers_rules_updated_entities.append(item.get("object"))

            except Exception as e:
                msg = (
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", '
                    f'search failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
                )
                get_effective_logger().error(msg)

            # log
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", wlk_outliers_rules_update_counter="{wlk_outliers_rules_update_counter}", wlk_outliers_rules_updated_entities="{json.dumps(wlk_outliers_rules_updated_entities, indent=2)}", search="{wlk_outliers_rules_update_search}"'
            )

        #
        # End version 2.0.72
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2072, procedure terminated'
    )
    return True


"""
In this function:
- Update the vtenant accounts to define adaptive_delay
- Create a new KVstore collection for wlk to store last seen activity per type of data
- Support overlap in the searches with deduplication for a safer collection of Wlk metrics
"""


def trackme_schema_upgrade_2075(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2075, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        #
        # Adaptive trackers
        #

        components_to_process = []
        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Update the adaptive delay tracker
            #

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with adaptive delay tracker update'
            )

            # report name
            tracker_name = (
                f"trackme_{component}_adaptive_delay_tracker_tenant_{tenant_id}"
            )

            # get the current search definition
            try:
                tracker_current = service.saved_searches[tracker_name]
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                )
                continue

            tracker_current_search = tracker_current.content.get("search")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
            )

            # add our new parameter
            tracker_new_search = f"{tracker_current_search} max_auto_delay_sec=604800"

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_name,
                "report_search": tracker_new_search,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                )

        #
        # WLK: create new collection & transforms definition
        #

        # check components and add accordingly
        if (
            vtenant_record.get("tenant_wlk_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="wlk", processing with Workload tracker updates'
            )

            transform_name = f"trackme_wlk_last_seen_activity_tenant_{tenant_id}"
            collection_name = f"kv_trackme_wlk_last_seen_activity_tenant_{tenant_id}"
            transform_fields = collections_dict["trackme_wlk_last_seen_activity"]
            definition_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            #
            # Only continue if successful
            #

            # create the transform
            if kvstore_created:
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": definition_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                #
                # Trackers updates
                #

                # retrieve the list of scheduler reports to be processed
                collection_trackers_name = (
                    f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
                )
                collection_trackers = service.kvstore[collection_trackers_name]

                #
                # enhance scheduler execution to support deduplication
                #

                trackers_dict = {}
                trackers_to_process = []
                trackers_to_process_kos = []

                # get records from the KVstore
                trackers_records = collection_trackers.data.query()

                for tracker_record in trackers_records:
                    tracker_name = tracker_record.get("tracker_name")
                    tracker_kos = tracker_record.get("knowledge_objects")

                    # if the tracker_name starts by scheduler_
                    if re.search("^scheduler_", tracker_name):
                        trackers_to_process.append(tracker_name)
                        trackers_to_process_kos.append(tracker_kos)

                        trackers_dict[tracker_name] = {
                            "knowledge_objects": json.loads(tracker_kos),
                        }

                # loop through the trackers (wrapper)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # in tracker_current_search, replace the sentence: (if account is not local, double escape the quotes)
                    #  _index_earliest="-5m" _index_latest="now"
                    # with:
                    #  _index_earliest="-20m" _index_latest="now"
                    # | bucket _time span=5m

                    if tracker_account == "local":
                        tracker_new_search = re.sub(
                            r'_index_earliest="-5m" _index_latest="now"',
                            r'_index_earliest="-20m" _index_latest="now" earliest="-20m" latest="now"\n| eval orig_time = _time | bucket _time span=5m',
                            tracker_current_search,
                        )

                    else:
                        tracker_new_search = re.sub(
                            r'_index_earliest=\\"-5m\\" _index_latest=\\"now\\"',
                            r'_index_earliest=\\"-20m\\" _index_latest=\\"now\\" earliest=\\"-20m\\" latest=\\"now\\"\n| eval orig_time = _time | bucket _time span=5m',
                            tracker_current_search,
                        )

                    # only if remote, replace the sentence:
                    #  earliest="-10m" latest="now"
                    # with:
                    #  earliest="-20m" latest="now"

                    if tracker_account != "local":
                        tracker_new_search = re.sub(
                            r'earliest="-10m" latest="now"',
                            r'earliest="-20m" latest="now"',
                            tracker_new_search,
                        )

                    # replace the sentence:
                    # | stats count(eval(status
                    # with:
                    # | stats max(_time) as _time, count(eval(status

                    tracker_new_search = re.sub(
                        r"\| stats count\(eval\(status",
                        r"| stats max(_time) as _time, count(eval(status",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # by app, user, savedsearch_name
                    # with:
                    # by _time, app, user, savedsearch_name

                    tracker_new_search = re.sub(
                        r"by app, user, savedsearch_name",
                        r"by orig_time, app, user, savedsearch_name",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # | fields app, user, savedsearch_name, count_completed
                    # with:
                    # | fields last_seen, app, user, savedsearch_name, count_completed

                    tracker_new_search = re.sub(
                        r"\| fields app, user, savedsearch_name, count_completed",
                        r"| fields _time, app, user, savedsearch_name, count_completed",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # context="live"
                    # with:
                    # context="live" check_last_seen=True check_last_seen_field=last_seen_scheduler

                    tracker_new_search = re.sub(
                        r"context=\"live\"",
                        r"context=live check_last_seen=True check_last_seen_field=last_seen_scheduler",
                        tracker_new_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                # loop through the trackers (tracker)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_tracker_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # replace the sentence:
                    # earliest="-10m" latest="now"
                    # with:
                    # earliest="-20m" latest="now"

                    tracker_new_search = re.sub(
                        r'earliest="-10m" latest="now"',
                        r'earliest="-20m" latest="now"',
                        tracker_current_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                #
                # enhance introspection execution to support deduplication
                #

                trackers_dict = {}
                trackers_to_process = []
                trackers_to_process_kos = []

                # get records from the KVstore
                trackers_records = collection_trackers.data.query()

                for tracker_record in trackers_records:
                    tracker_name = tracker_record.get("tracker_name")
                    tracker_kos = tracker_record.get("knowledge_objects")

                    # if the tracker_name starts by scheduler_
                    if re.search("^introspection_", tracker_name):
                        trackers_to_process.append(tracker_name)
                        trackers_to_process_kos.append(tracker_kos)

                        trackers_dict[tracker_name] = {
                            "knowledge_objects": json.loads(tracker_kos),
                        }

                # loop through the trackers (wrapper)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # in tracker_current_search, replace the sentence: (if account is not local, double escape the quotes)
                    #  _index_earliest="-5m" _index_latest="now"
                    # with:
                    #  _index_earliest="-20m" _index_latest="now"
                    # | bucket _time span=5m

                    if tracker_account == "local":
                        tracker_new_search = re.sub(
                            r'_index_earliest="-5m" _index_latest="now"',
                            r'_index_earliest="-20m" _index_latest="now" earliest="-20m" latest="now"',
                            tracker_current_search,
                        )

                    else:
                        tracker_new_search = re.sub(
                            r'_index_earliest=\\"-5m\\" _index_latest=\\"now\\"',
                            r'_index_earliest=\\"-20m\\" _index_latest=\\"now\\" earliest=\\"-20m\\" latest=\\"now\\"',
                            tracker_current_search,
                        )

                    # only if remote, replace the sentence:
                    #  earliest="-10m" latest="now"
                    # with:
                    #  earliest="-20m" latest="now"

                    if tracker_account != "local":
                        tracker_new_search = re.sub(
                            r'earliest="-10m" latest="now"',
                            r'earliest="-20m" latest="now"',
                            tracker_new_search,
                        )

                    # replace the sentence:
                    # | stats max(_time) as last_time, avg(elapsed) as elapsed, avg(pct_cpu) as pct_cpu
                    # with:
                    # | eval orig_time = _time | bucket orig_time span=5m | stats max(_time) as last_time, avg(elapsed) as elapsed, avg(pct_cpu) as pct_cpu

                    tracker_new_search = re.sub(
                        r"\| stats max\(_time\) as last_time, avg\(elapsed\) as elapsed, avg\(pct_cpu\) as pct_cpu",
                        r"| eval orig_time = _time | bucket orig_time span=5m | stats max(_time) as _time, avg(elapsed) as elapsed, avg(pct_cpu) as pct_cpu",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # by object, app, savedsearch_name
                    # with:
                    # by _time, object, app, savedsearch_name

                    tracker_new_search = re.sub(
                        r"by object, app, savedsearch_name",
                        r"by orig_time, object, app, savedsearch_name",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # | fields object, object_id, app, savedsearch_name, last_time, elapsed, pct_cpu, pct_memory, scan_count, type, user, group
                    # with:
                    # | fields object, object_id, app, savedsearch_name, last_seen, elapsed, pct_cpu, pct_memory, scan_count, type, user, group

                    tracker_new_search = re.sub(
                        r"\| fields object, object_id, app, savedsearch_name, last_time, elapsed, pct_cpu, pct_memory, scan_count, type, user, group",
                        r"| fields _time, object, object_id, app, savedsearch_name, elapsed, pct_cpu, pct_memory, scan_count, type, user, group",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # context="live"
                    # with:
                    # context="live" check_last_seen=True check_last_seen_field=last_seen_introspection

                    tracker_new_search = re.sub(
                        r"context=\"live\"",
                        r"context=live check_last_seen=True check_last_seen_field=last_seen_introspection",
                        tracker_new_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                # loop through the trackers (tracker)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_tracker_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # replace the sentence:
                    # earliest="-10m" latest="now"
                    # with:
                    # earliest="-20m" latest="now"

                    tracker_new_search = re.sub(
                        r'earliest="-10m" latest="now"',
                        r'earliest="-20m" latest="now"',
                        tracker_current_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                #
                # enhance notable execution to support deduplication
                #

                trackers_dict = {}
                trackers_to_process = []
                trackers_to_process_kos = []

                # get records from the KVstore
                trackers_records = collection_trackers.data.query()

                for tracker_record in trackers_records:
                    tracker_name = tracker_record.get("tracker_name")
                    tracker_kos = tracker_record.get("knowledge_objects")

                    # if the tracker_name starts by scheduler_
                    if re.search("^notable_", tracker_name):
                        trackers_to_process.append(tracker_name)
                        trackers_to_process_kos.append(tracker_kos)

                        trackers_dict[tracker_name] = {
                            "knowledge_objects": json.loads(tracker_kos),
                        }

                # loop through the trackers (wrapper)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # in tracker_current_search, replace the sentence: (if account is not local, double escape the quotes)
                    #  _index_earliest="-5m" _index_latest="now"
                    # with:
                    #  _index_earliest="-20m" _index_latest="now"
                    # | bucket _time span=5m

                    if tracker_account == "local":
                        tracker_new_search = re.sub(
                            r'_index_earliest="-5m" _index_latest="now"',
                            r'_index_earliest="-20m" _index_latest="now" earliest="-20m" latest="now"',
                            tracker_current_search,
                        )

                    else:
                        tracker_new_search = re.sub(
                            r'_index_earliest=\\"-5m\\" _index_latest=\\"now\\"',
                            r'_index_earliest=\\"-20m\\" _index_latest=\\"now\\" earliest=\\"-20m\\" latest=\\"now\\"',
                            tracker_current_search,
                        )

                    # only if remote, replace the sentence:
                    #  earliest="-10m" latest="now"
                    # with:
                    #  earliest="-20m" latest="now"

                    if tracker_account != "local":
                        tracker_new_search = re.sub(
                            r'earliest="-10m" latest="now"',
                            r'earliest="-20m" latest="now"',
                            tracker_new_search,
                        )

                    # replace the sentence:
                    # by source
                    # with:
                    # by _time, source span=5m

                    tracker_new_search = re.sub(
                        r"by source",
                        r"by _time, source span=5m",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # | fields app, user, savedsearch_name, count_ess_notable, group, object, object_id
                    # with:
                    # | fields last_seen, app, user, savedsearch_name, count_ess_notable, group, object, object_id

                    tracker_new_search = re.sub(
                        r"\| fields app, user, savedsearch_name, count_ess_notable, group, object, object_id",
                        r"| fields _time, app, user, savedsearch_name, count_ess_notable, group, object, object_id",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # context="live"
                    # with:
                    # context="live" check_last_seen=True check_last_seen_field=last_seen_notable

                    tracker_new_search = re.sub(
                        r"context=\"live\"",
                        r"context=live check_last_seen=True check_last_seen_field=last_seen_notable",
                        tracker_new_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                # loop through the trackers (tracker)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_tracker_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # replace the sentence:
                    # earliest="-10m" latest="now"
                    # with:
                    # earliest="-20m" latest="now"

                    tracker_new_search = re.sub(
                        r'earliest="-10m" latest="now"',
                        r'earliest="-20m" latest="now"',
                        tracker_current_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                #
                # enhance splunkcloud_svc execution to support deduplication
                #

                trackers_dict = {}
                trackers_to_process = []
                trackers_to_process_kos = []

                # get records from the KVstore
                trackers_records = collection_trackers.data.query()

                for tracker_record in trackers_records:
                    tracker_name = tracker_record.get("tracker_name")
                    tracker_kos = tracker_record.get("knowledge_objects")

                    # if the tracker_name starts by scheduler_
                    if re.search("^splunkcloud_svc_", tracker_name):
                        trackers_to_process.append(tracker_name)
                        trackers_to_process_kos.append(tracker_kos)

                        trackers_dict[tracker_name] = {
                            "knowledge_objects": json.loads(tracker_kos),
                        }

                # loop through the trackers (wrapper)
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # in tracker_current_search, replace the sentence: (if account is not local, double escape the quotes)
                    #  _index_earliest="-15m" _index_latest="now"
                    # with:
                    #  _index_earliest="-3h" _index_latest="now"

                    if tracker_account == "local":
                        tracker_new_search = re.sub(
                            r'_index_earliest="-15m" _index_latest="now"',
                            r'_index_earliest="-3h" _index_latest="now" earliest="--3h" latest="now"',
                            tracker_current_search,
                        )

                    else:
                        tracker_new_search = re.sub(
                            r'_index_earliest=\\"-15m\\" _index_latest=\\"now\\"',
                            r'_index_earliest=\\"-3h\\" _index_latest=\\"now\\" earliest=\\"-3h\\" latest=\\"now\\"',
                            tracker_current_search,
                        )

                    # replace the sentence:
                    # | fields app, group, object, object_id, savedsearch_name, user, svc_usage
                    # with:
                    # | fields _time, app, group, object, object_id, savedsearch_name, user, svc_usage

                    tracker_new_search = re.sub(
                        r"\| fields app, group, object, object_id, savedsearch_name, user, svc_usage",
                        r"| fields _time, app, group, object, object_id, savedsearch_name, user, svc_usage",
                        tracker_new_search,
                    )

                    # replace the sentence:
                    # context="live"
                    # with:
                    # context="live" check_last_seen=True check_last_seen_field=last_seen_splunkcloud_svc

                    tracker_new_search = re.sub(
                        r"context=\"live\"",
                        r"context=live check_last_seen=True check_last_seen_field=last_seen_splunkcloud_svc",
                        tracker_new_search,
                    )

                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": "-20m",
                        "latest_time": "now",
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

                # Notes: updating trackers for splunkcloud_svc is not required

            #
            # ML Outliers: mass update rules for wlk
            #

            # set kwargs
            kwargs_wlk_outliers_rules_update = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # define the gen search
            wlk_outliers_rules_update_search = remove_leading_spaces(
                f"""\
                | inputlookup trackme_wlk_outliers_entity_rules_tenant_{tenant_id} | eval keyid=_key
                ``` mass update the time_factor ```
                | where match(entities_outliers, "%H")
                | rex field=entities_outliers mode=sed "s/\\\"time_factor\\\": \\\"%H\\\"/\\\"time_factor\\\": \\\"none\\\"/g"
                ``` force update the confidence and confidence_reason ```
                | eval confidence="low", confidence_reason="upgrade to TrackMe 2.0.72 for splk-wlk requires models to be trained again due to the change of the time_factor field, which will happen automatically as soon as possible."
                | outputlookup append=t key_field=keyid trackme_wlk_outliers_entity_rules_tenant_{tenant_id}
                """
            )

            wlk_outliers_rules_update_counter = 0
            wlk_outliers_rules_updated_entities = []

            # run search

            # track the search runtime
            start = time.time()

            # proceed
            try:
                reader = run_splunk_search(
                    service,
                    wlk_outliers_rules_update_search,
                    kwargs_wlk_outliers_rules_update,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        wlk_outliers_rules_update_counter += 1
                        wlk_outliers_rules_updated_entities.append(item.get("object"))

            except Exception as e:
                msg = (
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", '
                    f'search failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
                )
                get_effective_logger().error(msg)

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2075, procedure terminated'
    )
    return True


"""
In this function:
- Update the adaptive delay report to add the new option max_changes_past_7days
"""


def trackme_schema_upgrade_2078(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2078, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Adaptive trackers
        #

        components_to_process = []
        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Update the adaptive delay tracker
            #

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with adaptive delay tracker update'
            )

            # report name
            tracker_name = (
                f"trackme_{component}_adaptive_delay_tracker_tenant_{tenant_id}"
            )

            # get the current search definition
            try:
                tracker_current = service.saved_searches[tracker_name]
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                )
                continue

            tracker_current_search = tracker_current.content.get("search")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
            )

            # add our new parameter
            tracker_new_search = f"{tracker_current_search} max_changes_past_7days=10"

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_name,
                "report_search": tracker_new_search,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2078, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2078, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2078, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2078, procedure terminated'
    )
    return True


"""
In this function:
- Update the vtenant accounts to define the value for alias
- Update the logical group KVstore collection transforms
"""


def trackme_schema_upgrade_2083(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2083, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # prepare transforms updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # transforms updates
        #

        transform_name = f"trackme_common_logical_group_tenant_{tenant_id}"
        collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        transform_fields = collections_dict["trackme_common_logical_group"]
        transform_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # delete the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        # create the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
            "transform_fields": transform_fields,
            "collection_name": collection_name,
            "transform_acl": transform_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2083, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2083, procedure terminated'
    )
    return True


"""
In this function:
- Run a RBAC force check and update to ensure permissions of the tenant are correctly set (due to a bug affecting previous updates)
- Create the new dsm tags KVstore collection
- Reflects updates the splk-dsm main kvstore transforms
- Update splk-dsm abstract trackers to include global_dcount_host
- Migrate all ML models to splunk-system-user ownership, remove orphans models
- Ensures that the common trackme_common_replica_trackers Kvcollection and transforms have been created for the tenant
"""


def trackme_schema_upgrade_2084(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2084, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # RBAC force check and update
        #

        tenant_id = vtenant_record.get("tenant_id")
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/vtenants/admin/update_tenant_rbac'
        data = {
            "tenant_id": {tenant_id},
            "tenant_roles_admin": vtenant_record.get("tenant_roles_admin"),
            "tenant_roles_power": vtenant_record.get("tenant_roles_user"),
            "tenant_roles_user": vtenant_record.get("tenant_roles_power"),
            "tenant_owner": vtenant_record.get("tenant_owner"),
        }

        # update the account
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=data,
                verify=False,
                timeout=1800,  # 30 minutes timeout, on extremely large env, this can take a while
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, RBAC check and update has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, RBAC check and update was operated successfully, response.status_code="{response.status_code}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, RBAC check and update has failed, exception="{str(e)}"'
            )

        #
        # dsm_tags KVstore collection
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:

            # get permissions
            tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
                vtenant_record
            )

            # TrackMe sharing level
            trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            # set
            transform_name = f"trackme_dsm_tags_tenant_{tenant_id}"
            collection_name = f"kv_trackme_dsm_tags_tenant_{tenant_id}"
            transform_fields = collections_dict["trackme_dsm_tags"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the tracker report
            report_name = f"trackme_dsm_tags_tracker_tenant_{tenant_id}"
            report_search = f'| trackmesplktags tenant_id="{tenant_id}"'
            report_properties = {
                "description": "This scheduled report applies and maintains tags policies for the splk-dsm component",
                "is_scheduled": True,
                "cron_schedule": "*/15 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

            # Execute tags update now
            # trackme-limited/trackme-report-issues#840: this operation is not required anymore

        #
        # Update splk-dsm transform
        #

        # check components and add accordingly
        objects_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update splk-dsm abstract trackers to include global_dcount_host
        #

        if vtenant_record.get("tenant_dsm_enabled") == 1:

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_dsm_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_abstract_to_process = []
            trackers_wrapper_to_process = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:

                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = json.loads(tracker_record.get("knowledge_objects"))

                tracker_reports = tracker_kos.get("reports")

                for tracker_report in tracker_reports:
                    # if the tracker_name contains the word "_abstract_":
                    if "_abstract_" in tracker_report:
                        trackers_abstract_to_process.append(tracker_report)
                    # if the tracker_name contains the word "_wrapper_":
                    elif "_wrapper_" in tracker_report:
                        trackers_wrapper_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_abstract_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace the sentence:
                #  max(data_last_time_seen) as data_last_time_seen by
                # with:
                #  max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by

                tracker_new_search = re.sub(
                    r"max\(data_last_time_seen\) as data_last_time_seen by",
                    r"max(data_last_time_seen) as data_last_time_seen, max(dcount_host) as global_dcount_host by",
                    tracker_current_search,
                )

                # in tracker_current_search, replace the sentence:
                # sum(data_eventcount) as data_eventcount by
                # with:
                # sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host

                tracker_new_search = re.sub(
                    r"sum\(data_eventcount\) as data_eventcount by",
                    r"sum(data_eventcount) as data_eventcount, first(global_dcount_host) as global_dcount_host by",
                    tracker_new_search,
                )

                # in tracker_current_search, replace the sentence:
                # eval dcount_host=round(latest_dcount_host_5m, 2)
                # with:
                # eval dcount_host=round(global_dcount_host, 0)

                tracker_new_search = re.sub(
                    r"eval dcount_host=round\(latest_dcount_host_5m, 2\)",
                    r"eval dcount_host=round(global_dcount_host, 0)",
                    tracker_new_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

            # loop through wrapper reports
            for tracker_name in trackers_wrapper_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]                
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace the sentence:
                # metric_name:trackme.splk.feeds.stdev_dcount_host_5m=stdev_dcount_host_5m,
                # with:
                # metric_name:trackme.splk.feeds.stdev_dcount_host_5m=stdev_dcount_host_5m, metric_name:trackme.splk.feeds.global_dcount_host=global_dcount_host,

                tracker_new_search = re.sub(
                    r"metric_name:trackme.splk.feeds.stdev_dcount_host_5m=stdev_dcount_host_5m,",
                    r"metric_name:trackme.splk.feeds.stdev_dcount_host_5m=stdev_dcount_host_5m, metric_name:trackme.splk.feeds.global_dcount_host=global_dcount_host,",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # Migrate all ML models to splunk-system-user ownership, remove orphans models
        #

        """
        Get all records from an ML rules collection.

        :param collection: The collection to query.
        :return: A list of records, a dictionary of records, a list of keys.
        """

        def get_ml_rules_collection(collection):
            collection_records = []
            collection_records_dict = {}
            count_to_process_list = []

            end = False
            skip_tracker = 0
            while not end:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if process_collection_records:
                    for item in process_collection_records:
                        collection_records.append(item)
                        collection_records_dict[item.get("_key")] = (
                            item  # Add the entire item to the dictionary
                        )
                        count_to_process_list.append(item.get("_key"))
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            return collection_records, collection_records_dict, count_to_process_list

        """
        Removes an orphan Machine Learning model from the collection.

        :param component: The component name.
        :param rest_url: The REST URL to use.
        :param header: The header to use.
        :param ml_model_lookup_name: The Machine Learning model lookup name.
        :return: True if the model was removed successfully, otherwise False.
        
        """

        def remove_ml_model(component, rest_url, header, ml_model_lookup_name):

            get_effective_logger().info(
                f'component="{component}", context="inspect_collection:outliers", attempting to delete orphan Machine Learning lookup_name="{ml_model_lookup_name}"'
            )
            try:
                response = requests.delete(
                    rest_url,
                    headers=header,
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (
                    200,
                    201,
                    204,
                ):
                    error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", failure to delete ML lookup_name="{ml_model_lookup_name}", url="{rest_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    raise Exception(error_msg)
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", action="success", deleted lookup_name="{ml_model_lookup_name}" successfully'
                    )
                    return True

            except Exception as e:
                error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", failure to delete ML lookup_name="{ml_model_lookup_name}" with exception="{str(e)}"'
                raise Exception(error_msg)

        """
        Reasign a Machine Learning model to the Splunk system user.

        :param model_id: The model_id to reassign.
        :param rest_url: The REST URL to use.
        :param header: The header to use.

        :return: True if the model was reassigned successfully, otherwise False.

        """

        def reassign_ml_model(model_id, rest_url, header):

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", attempting to re-assign model_id="{model_id}" to splunk-system-user'
            )

            acl_properties = {
                "sharing": "user",
                "owner": "splunk-system-user",
            }

            # proceed boolean
            proceed = False

            # before re-assigning, check if the model exist by running a GET request, if the status code is different from 2**, do not proceed and log an informational message instead
            try:
                response = requests.get(
                    f"{rest_url}",
                    headers=header,
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", model_id="{model_id}" does not exist, it might have been re-assigned in the meantime, skipping re-assignment'
                    )
                    return False
                else:
                    proceed = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", model_id="{model_id}" failed to retrieve model, exception="{str(e)}"'
                )

            if proceed:

                # re-assign post
                try:
                    response = requests.post(
                        f"{rest_url}/acl",
                        headers=header,
                        data=acl_properties,
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (
                        200,
                        201,
                        204,
                    ):
                        error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", failure to reassign model_id="{model_id}", url="{rest_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                        raise Exception(error_msg)
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", action="success", model_id="{model_id}" reassigned successfully'
                        )
                        return True

                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", action="failure", model_id="{model_id}" reassigned failed, exception="{str(e)}"'
                    )
                    raise Exception(str(e))

        # get all vtenants records, this job is not tenant specific
        vtenant_records = collection_vtenants.data.query()

        # A list to store ml_rules_outliers_collections
        ml_rules_outliers_collections = []

        # A dict to ml models definitions
        ml_models_dict = {}

        # A list to store ml models currently configured
        ml_models_list = []

        for vtenant_record in vtenant_records:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", processing vtenant_record={json.dumps(vtenant_record, indent=2)}'
            )

            # get the tenant_id
            tenant_id = vtenant_record.get("tenant_id")

            # for component in dsm, dhm, flx
            for component in ["dsm", "dhm", "flx"]:

                # get status
                component_status = vtenant_record.get(f"tenant_{component}_enabled")

                # append the collection
                if component_status == 1:
                    ml_rules_outliers_collections.append(
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    )

        # for each outliers rules collection
        for ml_rules_collection_name in ml_rules_outliers_collections:

            # connect to the collection service and retrieve the records
            ml_rules_collection = service.kvstore[ml_rules_collection_name]

            # extract ml_rules_tenant_id from the collection name: trackme_<component>_outliers_entity_rules_tenant_<ml_rules_tenant_id>
            ml_rules_tenant_id = ml_rules_collection_name.split("_")[-1]

            # get records
            try:
                ml_rules_records, ml_rules_records_dict, ml_rules_records_count = (
                    get_ml_rules_collection(ml_rules_collection)
                )

                for ml_rules_record in ml_rules_records:

                    # get key
                    ml_rules_record_key = ml_rules_record.get("_key")

                    # get dictionary entities_outliers from the field entities_outliers
                    entities_outliers = json.loads(
                        ml_rules_record.get("entities_outliers")
                    )

                    # loop through entities_outliers, the dict key is the model_id
                    for ml_model_entity in entities_outliers:

                        ml_models_dict[ml_model_entity] = {
                            "model_id": ml_model_entity,
                            "collection_name": ml_rules_collection_name,
                            "collection_key": ml_rules_record_key,
                            "tenant_id": ml_rules_tenant_id,
                        }
                        ml_models_list.append(
                            f"__mlspl_{ml_model_entity}.mlmodel"
                        )  # this is the filename

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", failed to retrieve the records from the collection, collection_name="{ml_rules_collection_name}", exception="{str(e)}"'
                )

            # log
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", {len(ml_models_dict)} ML models were found configured in TrackMe collections, will now start inspecting Splunk existing models.'
            )

        # run the following search to retrieve the list of existing ML models

        # Define the query
        search = f'| rest splunk_server=local timeout=1200 "/servicesNS/nobody/trackme/data/lookup-table-files" | search eai:acl.app="trackme" AND title="__mlspl_model_*.mlmodel" | search [ | `splk_outliers_get_model_files_for_tenant({tenant_id},{component})` | rename ml_model_filename as title | table title | format ] | table title, id'

        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }

        # A list to store current ml models (filename)
        ml_models_current_list = []

        # A dict to store the existing models
        ml_models_dict_existing = {}

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
                    ml_models_current_list.append(
                        item.get("title")
                    )  # this is the model filename
                    ml_models_dict_existing[item.get("title")] = {"id": item.get("id")}

        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", failed to retrieve the list of ML models, exception="{str(e)}"'
            )

        # log the number of currently existing models
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, subcontext="mlmodels-migration", {len(ml_models_current_list)} ML models were found in the system, starting orphan models inspection and migration'
        )

        #
        # orphan models purge / reassign
        #

        ml_models_purged_success_count = 0
        ml_models_purged_failures_count = 0
        ml_models_reassigned_success_count = 0
        ml_models_reassigned_failures_count = 0

        header = {
            "Authorization": "Splunk %s" % reqinfo["session_key"],
            "Content-Type": "application/json",
        }

        # for each model in ml_models_current_list, if the model is not in ml_models_list, delete it
        for model_id in ml_models_current_list:
            if model_id != "pending":
                if model_id not in ml_models_list:
                    # remove the model
                    rest_url = ml_models_dict_existing[model_id].get("id")

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="mlmodels-migration", attempting removal of model_id={model_id}"'
                    )

                    try:
                        remove_ml_model("trackme", rest_url, header, model_id)
                        ml_models_purged_success_count += 1
                    except Exception as e:
                        ml_models_purged_failures_count += 1
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="mlmodels-migration", failed to remove the orphan model, model_id="{model_id}", exception="{str(e)}"'
                        )

                elif model_id in ml_models_list:
                    # reassign the model
                    rest_url = ml_models_dict_existing[model_id].get("id")

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="mlmodels-migration", attempting reassignment of model_id={model_id}"'
                    )

                    try:
                        reassigned_model = reassign_ml_model(
                            model_id,
                            rest_url,
                            header,
                        )
                        if reassigned_model:
                            ml_models_reassigned_success_count += 1
                    except Exception as e:
                        ml_models_reassigned_failures_count += 1
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="mlmodels-migration", failed to reassign the model, model_id="{model_id}", exception="{str(e)}"'
                        )

        # log
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="mlmodels-migration", {ml_models_purged_success_count} orphan ML models were removed, {ml_models_purged_failures_count} orphan ML models removals failed, {ml_models_reassigned_success_count} ML models were reassigned to splunk-system-user, {ml_models_reassigned_failures_count} ML models reassignments failed'
        )

        """
        Ensures that the common trackme_common_replica_trackers Kvcollection and transforms have been created for the tenant            
        """

        # proceed boolean
        proceed = False

        # first, check if we have a transforms existing for the tenant, if not we need to proceed, otherwise we have nothing to do

        # transform name
        transform_name = f"trackme_common_replica_trackers_tenant_{tenant_id}"

        # check first if the transforms exists, if it does not exist, we do not need to proceed
        try:
            transform_current = service.confs["transforms"][transform_name]
            proceed = False
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", transform does exist, we do not need to proceed, transform="{transform_name}"'
            )
        except Exception as e:
            proceed = True
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", transform does not exist, we need to proceed, transform="{transform_name}"'
            )

        if proceed:

            # get permissions
            tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
                vtenant_record
            )

            # TrackMe sharing level
            trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            # set
            transform_name = f"trackme_common_replica_trackers_tenant_{tenant_id}"
            collection_name = f"kv_trackme_common_replica_trackers_tenant_{tenant_id}"
            transform_fields = collections_dict["trackme_common_replica_trackers"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2084, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2084, procedure terminated'
    )
    return True


"""
In this function:
- Decomission the datagen KVstore
- Address an issue with allowlist for splk-dhm/splk-mhm where the is_rex field was missing in the transforms definition
"""


def trackme_schema_upgrade_2087(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2087, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Decomission datagen KVstore
        #

        transform_name = f"trackme_common_datagen_cache_tenant_{tenant_id}"
        collection_name = f"kv_{transform_name}"

        # delete the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        # delete the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the KVstore collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", successfully deleted KVstore collection, collection="{collection_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the KVstore collection collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # Update splk-dhm/mhm allowlists transform
        #

        # check components and add accordingly
        objects_to_process = []

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("mhm")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        for component_toprocess in objects_to_process:
            transform_name = (
                f"trackme_{component_toprocess}_allowlist_tenant_{tenant_id}"
            )
            collection_name = f"kv_{transform_name}"
            transform_fields = collections_dict[
                f"trackme_{component_toprocess}_allowlist"
            ]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2087, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2087, procedure terminated'
    )
    return True


"""
In this function:
- Update main KVstore transforms definitions to include a new field "ctime" (creation time)
- For dsm/dhm/mhm, force an update of blocklists, if any, so we convert wildcards non regex to regex via the API automatically
"""


def trackme_schema_upgrade_2089(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2089, tenant_id="{tenant_id}"'
    )
    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        #
        # Update main KVstore transforms definitions to include a new field "ctime" (creation time)
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append("trackme_dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append("trackme_dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            objects_to_process.append("trackme_mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append("trackme_flx")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            objects_to_process.append("trackme_wlk")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        for object_name in objects_to_process:
            transform_name = "%s_tenant_%s" % (object_name, tenant_id)
            collection_name = "kv_%s_tenant_%s" % (object_name, tenant_id)
            transform_fields = collections_dict[object_name]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # For dsm/dhm/mhm, force an update of blocklists, if any, so we convert wildcards non regex to regex via the API automatically
        #

        components_suffix_list = []

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_suffix_list.append("dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_suffix_list.append("dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_suffix_list.append("mhm")

        # for each component suffix
        for component_suffix in components_suffix_list:

            # entities KV collection
            blocklist_collection_name = (
                f"kv_trackme_{component_suffix}_allowlist_tenant_{tenant_id}"
            )
            blocklist_collection = service.kvstore[blocklist_collection_name]

            # get records
            blocklist_records, blocklist_collection_keys, blocklist_collection_dict = (
                get_kv_collection(blocklist_collection, blocklist_collection_name)
            )

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", blocklist_records_count="{len(blocklist_records)}"'
            )

            if len(blocklist_records) > 0:

                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/splk_blocklist/write/blocklist_update'
                data = {
                    "tenant_id": f"{tenant_id}",
                    "component": f"{component_suffix}",
                    "records_list": json.dumps(blocklist_records),
                    "update_comment": "TrackMe schema upgrade for version 2.0.89",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", call to blocklist_update, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully called blocklist_update, component="{component_suffix}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to call to blocklist_update, component="{component_suffix}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2089, procedure terminated'
    )
    return True


"""
In this function:
- Create the new priority collection for dsm/dhm/mhm/flx/wlk
"""


def trackme_schema_upgrade_2090(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2090, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        #
        # For dsm/dhm/mhm, force an update of blocklists, if any, so we convert wildcards non regex to regex via the API automatically
        #

        components_suffix_list = []

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_suffix_list.append("dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_suffix_list.append("dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_suffix_list.append("mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_suffix_list.append("flx")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_suffix_list.append("wlk")

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # for each component suffix
        for component_suffix in components_suffix_list:

            #
            # priority policies collection
            #

            # set
            transform_name = (
                f"trackme_{component_suffix}_priority_policies_tenant_{tenant_id}"
            )
            collection_name = (
                f"kv_trackme_{component_suffix}_priority_policies_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[
                f"trackme_{component_suffix}_priority_policies"
            ]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            #
            # priority collection
            #

            # set
            transform_name = f"trackme_{component_suffix}_priority_tenant_{tenant_id}"
            collection_name = (
                f"kv_trackme_{component_suffix}_priority_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[f"trackme_{component_suffix}_priority"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            # create the tracker report
            report_name = (
                f"trackme_{component_suffix}_priority_tracker_tenant_{tenant_id}"
            )
            report_search = f'| trackmesplkpriority tenant_id="{tenant_id}" component={component_suffix}'
            report_properties = {
                "description": f"This scheduled report applies and maintains priority policies for the splk-{component_suffix} component",
                "is_scheduled": True,
                "cron_schedule": "*/15 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2090, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2090, procedure terminated'
    )
    return True


"""
In this function:
- Update main collections to include the sla_class per entity
- Create the new sla collection for dsm/dhm/mhm/flx/wlk
"""


def trackme_schema_upgrade_2091(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2091, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        components_suffix_list = []

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_suffix_list.append("dsm")

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_suffix_list.append("dhm")

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_suffix_list.append("mhm")

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_suffix_list.append("flx")

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_suffix_list.append("wlk")

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # for each component suffix
        for component_suffix in components_suffix_list:

            #
            # main transform collection
            #

            # set
            transform_name = f"trackme_{component_suffix}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component_suffix}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component_suffix}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            #
            # sla policies collection
            #

            # set
            transform_name = (
                f"trackme_{component_suffix}_sla_policies_tenant_{tenant_id}"
            )
            collection_name = (
                f"kv_trackme_{component_suffix}_sla_policies_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[
                f"trackme_{component_suffix}_sla_policies"
            ]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            #
            # sla collection
            #

            # set
            transform_name = f"trackme_{component_suffix}_sla_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component_suffix}_sla_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component_suffix}_sla"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            # create the tracker report
            report_name = f"trackme_{component_suffix}_sla_tracker_tenant_{tenant_id}"
            report_search = f'| trackmesplkslaclass tenant_id="{tenant_id}" component={component_suffix}'
            report_properties = {
                "description": f"This scheduled report applies and maintains SLA policies for the splk-{component_suffix} component",
                "is_scheduled": True,
                "cron_schedule": "*/15 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2091, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2091, procedure terminated'
    )
    return True


"""
In this function:
- Update the Workload main KVstore lookup transforms to include scheduler related fields (issue#631)
"""


def trackme_schema_upgrade_2094(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2094, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Components updates
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        components_suffix_list = []

        # check components and add accordingly
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_suffix_list.append("wlk")

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # for each component suffix
        for component_suffix in components_suffix_list:

            #
            # main transform collection
            #

            # set
            transform_name = f"trackme_{component_suffix}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component_suffix}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component_suffix}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2094, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2094, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2094, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2094, procedure terminated'
    )
    return True


"""
In this function:
- Update the Virtual Tenant account preferences to include the default_priority parameter

Note: this migration historically also created the per-tenant
``trackme_common_smartstatus_alert_action_last_seen_activity`` KV collection +
transform for the Smart Status alert action. That feature was decommissioned in
PR #1629 — the alert-action code is gone and the collection definition was
removed from ``collections_data.py``. The creation block was removed here so the
migration cannot ``KeyError`` on the now-absent ``collections_dict`` key when an
ancient tenant (``schema_version < 2095``) upgrades. Schema migration 2401 drops
any pre-existing smartstatus collection.
"""


def trackme_schema_upgrade_2095(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2095, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Vtenant account preferences
        #

        # get macros
        macros = service.confs["macros"]

        # get the
        try:
            macro_default_priority = macros["trackme_default_priority"].content[
                "definition"
            ]

            # the macro definition will be as:
            """
            eval priority=if(isnull(priority), "medium", priority)
            """

            # use a regex expression to extract the value of the priority level (low, medium, high, critical, pending), if we fail, we should assign medium
            macro_default_priority_level = re.search(
                r'eval\s+priority=if\(isnull\(priority\),\s+"(low|medium|high|critical|pending)",\s+priority\)',
                macro_default_priority,
            ).group(1)

        except Exception as e:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", failed to retrieve the current definition for the macro trackme_default_priority, will assign default to medium, exception={str(e)}'
            )
            macro_default_priority_level = "medium"

        # check, valid options are low, medium, high, critical, pending
        if macro_default_priority_level not in [
            "low",
            "medium",
            "high",
            "critical",
            "pending",
        ]:
            get_effective_logger().error(
                f'tenant_id="{tenant_id}", the macro trackme_default_priority has an invalid value="{macro_default_priority_level}", will assign default to medium'
            )
            macro_default_priority_level = "medium"

        #
        # Update the vtenant account configuration
        #

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Smart Status throttle collection — creation REMOVED (decommissioned).
        #
        # This migration historically created the per-tenant
        # trackme_common_smartstatus_alert_action_last_seen_activity KV
        # collection + transform here. The Smart Status alert action was
        # decommissioned in PR #1629: the alert-action code is gone and the
        # collection definition was removed from collections_data.py, so
        # `collections_dict["trackme_common_smartstatus_alert_action_last_seen_activity"]`
        # would now raise KeyError and halt the entire upgrade chain for any
        # tenant at schema_version < 2095. The creation block is removed so this
        # section is a safe no-op; schema migration 2401 drops any pre-existing
        # smartstatus collection. Guarded by
        # unit_tests/check_schema_collections_dict_keys.py.
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2095, procedure terminated'
    )
    return True


"""
In this function:
- Update the Virtual Tenant account preferences to include pagination_mode and pagination_size parameters
- Uodate the Adaptive delay tracker to include the review_period_no_days parameter
"""


def trackme_schema_upgrade_2096(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2096, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        # get macros
        pagination_mode = reqinfo["trackme_conf"]["trackme_general"]["pagination_mode"]
        pagination_size = reqinfo["trackme_conf"]["trackme_general"]["pagination_size"]

        #
        # Update the vtenant account configuration
        #

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            {"pagination_mode": pagination_mode, "pagination_size": pagination_size},
        )

        #
        # Adaptive delay tracker update
        #

        components_to_process = []
        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Update the adaptive delay tracker
            #

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with adaptive delay tracker update'
            )

            # report name
            tracker_name = (
                f"trackme_{component}_adaptive_delay_tracker_tenant_{tenant_id}"
            )

            # get the current search definition
            try:
                tracker_current = service.saved_searches[tracker_name]
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                )
                continue

            tracker_current_search = tracker_current.content.get("search")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
            )

            # add our new parameter
            tracker_new_search = f"{tracker_current_search} review_period_no_days=30"

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_name,
                "report_search": tracker_new_search,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2096, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2096, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2096, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2096, procedure terminated'
    )
    return True


"""
In this function:
- Update the Virtual Tenant account preferences to include ui_default_timerange parameter
- Update registered TrackMe alerts to call the new macro for applying the maintenance mode
- Update tenant Ack transforms definition
"""


def trackme_schema_upgrade_2097(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2097, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Purge any TrackMe entities containing backslashes in the object value
        #

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            # Define the query
            search = f'| inputlookup trackme_wlk_tenant_{tenant_id} | eval key = _key | where match(object, "\\\\\\\\") | table key, object'

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", searching for non encoded backslash entities, search="{search}"'
            )

            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # A list to store all executions
            results_list = []

            # A dict to store the results
            results_dict = {}

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
                        results_dict[item["key"]] = item["object"]
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", detected non encoded backslash entity to be purged, object="{item["object"]}", key="{item["key"]}"'
                        )

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", could not verify the presence of non encoded backslash entities, search permanently failed, exception="{str(e)}"'
                )

            # if the results_dict is not empty, we need to purge the entities
            if results_dict:
                # Data collection
                collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
                collection = service.kvstore[collection_name]

                # loop through the results dict and remove any entity from the KVstore
                for key, object_value in results_dict.items():
                    try:
                        collection.data.delete(json.dumps({"_key": key}))
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", successfully purged non encoded backslash entity, object="{object_value}", key="{key}"'
                        )
                        results_list.append(
                            {
                                "object": object_value,
                                "key": key,
                                "result": "successfully purged non encoded backslash entity",
                            }
                        )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", failed to purge non encoded backslash entity, object="{object_value}", key="{key}", exception="{str(e)}"'
                        )
                        results_list.append(
                            {
                                "object": object_value,
                                "key": key,
                                "result": "failure to purge non encoded backslash entity",
                                "exception": str(e),
                            }
                        )

            # log a message if there were no entities to be purged
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", component="{component}", no non encoded backslash entities to be purged'
                )

        #
        # Update the vtenant account configuration
        #

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update alerts
        #

        # get alert object from field tenant_alert_objects
        alert_objects = vtenant_record.get("tenant_alert_objects", None)

        # check if we have alert objects
        if alert_objects:

            # load the alert objects as a json object
            try:
                alert_objects = json.loads(alert_objects)
            except Exception as e:
                # log alerts to be updated
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", no alerts found for update.'
                )

            # get list of alerts
            alerts_list = alert_objects.get("alerts", [])

            # for each alert
            for alert_name in alerts_list:

                alert_current = None
                try:
                    alert_current = service.saved_searches[alert_name]
                except Exception as e:
                    pass

                if alert_current:
                    alert_current_search = alert_current.content.get("search")
                    alert_current_earliest_time = alert_current.content.get(
                        "dispatch.earliest_time"
                    )
                    alert_current_latest_time = alert_current.content.get(
                        "dispatch.latest_time"
                    )

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", alert_current_search="{alert_current_search}"'
                    )

                    """
                    in alert_current_search, replace the following sentence using regex:

                    appendcols [ | inputlookup trackme_maintenance_mode ] | filldown maintenance_mode | where NOT maintenance_mode="enabled"

                    by:

                    `trackme_apply_maintenance_mode`

                    """

                    alert_new_search = re.sub(
                        r'appendcols \[ \| inputlookup trackme_maintenance_mode \] \| filldown maintenance_mode \| where NOT maintenance_mode="enabled"',
                        r"`trackme_apply_maintenance_mode`",
                        alert_current_search,
                    )

                    # update the alert definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": alert_name,
                        "report_search": alert_new_search,
                        "earliest_time": alert_current_earliest_time,
                        "latest_time": alert_current_latest_time,
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", update alert definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", successfully updated alert definition, alert="{alert_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", failed to update the alert definition, report="{alert_name}", exception="{str(e)}"'
                        )

        #
        # Update Ack transforms definition
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # set
        transform_name = f"trackme_common_alerts_ack_tenant_{tenant_id}"
        collection_name = f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
        transform_fields = collections_dict["trackme_common_alerts_ack"]
        transform_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # delete the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        # create the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
            "transform_fields": transform_fields,
            "collection_name": collection_name,
            "transform_acl": transform_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2097, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2097, procedure terminated'
    )
    return True


"""
In this function:
 - Update the Virtual Tenant account preferences to include per component Tabulator groupBy
 - Extend the tags feature to all components, in addition with initial dsm only scope
 """


def trackme_schema_upgrade_2098(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2098, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the vtenant account configuration
        #

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Create tags tracker for newly eligible components
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            #
            # Create the tags collection and transforms (note for dsm, this collection already exists)
            #

            if component != "dsm":

                # set
                transform_name = f"trackme_{component}_tags_tenant_{tenant_id}"
                collection_name = f"kv_trackme_{component}_tags_tenant_{tenant_id}"
                transform_fields = collections_dict[f"trackme_{component}_tags"]
                ko_acl = {
                    "owner": vtenant_record.get("tenant_owner"),
                    "sharing": trackme_default_sharing,
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # create the KVstore collection
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
                data = {
                    "tenant_id": tenant_id,
                    "collection_name": collection_name,
                    "collection_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                kvstore_created = False
                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                        )
                        kvstore_created = True
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                    )

                # continue
                if kvstore_created:

                    # create the transform
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                    data = {
                        "tenant_id": tenant_id,
                        "transform_name": transform_name,
                        "transform_fields": transform_fields,
                        "collection_name": collection_name,
                        "transform_acl": ko_acl,
                        "owner": vtenant_record.get("tenant_owner"),
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                        )

            #
            # Create the tags policies collection and transforms (for all components)
            #

            # set
            transform_name = f"trackme_{component}_tags_policies_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_tags"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

            #
            # Create the report tracker (not for dsm, as it already exists)
            #

            if component != "dsm":

                report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # create the tracker report
                report_name = f"trackme_{component}_tags_tracker_tenant_{tenant_id}"
                report_search = (
                    f'| trackmesplktags tenant_id="{tenant_id}" component="{component}"'
                )
                report_properties = {
                    "description": f"This scheduled report applies and maintains tags policies for the splk-{component} component",
                    "is_scheduled": True,
                    "cron_schedule": "*/15 * * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }

                # create the report
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                    "report_search": report_search,
                    "report_properties": report_properties,
                    "report_acl": report_acl,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                    )

                # Execute tags update now
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/splk_tag_policies/write/tag_policies_apply'
                post_data = {
                    "tenant_id": tenant_id,
                    "component": component,
                }

                # update the account
                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(post_data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2098, tags apply operation has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2098, tags apply operation was executed successfully, response.status_code="{response.status_code}", response="{json.dumps(response.json(), indent=2)}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2098, tags apply operation has failed, exception="{str(e)}"'
                    )

            #
            # for dsm only:
            # - migrate existing policies to the new collection
            # - update the tracker report
            # - remove the decommissioned collection and transforms
            #

            if component == "dsm":

                #
                # migrate policies to the new collection
                #

                # Define the query
                search = f"| inputlookup trackme_common_tag_policies_tenant_{tenant_id} | eval key = _key | outputlookup append=t key_field=key trackme_{component}_tags_policies_tenant_{tenant_id}"

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", component="{component}", migrate tags policies, search="{search}"'
                )

                kwargs_oneshot = {
                    "earliest_time": "-5m",
                    "latest_time": "now",
                    "output_mode": "json",
                    "count": 0,
                }

                # a counter
                counter = 0

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
                            counter += 1

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", component="{component}", migrate tags policies, search successfully operated, records_updated="{counter}"'
                    )

                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", component="{component}", migrate tags policies, search permanently failed, exception="{str(e)}"'
                    )

                #
                # Update the tag tracker
                #

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with tags tracker update'
                )

                # report name
                tracker_name = f"trackme_dsm_tags_tracker_tenant_{tenant_id}"

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # add our new parameter
                tracker_new_search = f'{tracker_current_search} component="dsm"'

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

                #
                # Remove the decommissioned collection and transforms
                #

                # set
                transform_name = f"trackme_common_tag_policies_tenant_{tenant_id}"
                collection_name = f"kv_trackme_common_tag_policies_tenant_{tenant_id}"

                # delete the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # delete the KVstore collection
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvcollection'
                data = {
                    "tenant_id": tenant_id,
                    "collection_name": collection_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the KVstore collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", successfully deleted KVstore collection, collection="{collection_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2098, tenant_id="{tenant_id}", failed to delete the KVstore collection collection="{collection_name}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2098, procedure terminated'
    )
    return True


"""
In this function:
 - Addresses the transition from md5 hashlib to sha256 for FIPS
 """


def trackme_schema_upgrade_2099(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2099, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # md5 to sha256 migration
        #

        tenant_id = vtenant_record.get("tenant_id")

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            #
            # migrate records from md5 to sha256
            #

            if component in ("dsm", "dhm", "flx", "wlk", "mhm"):

                # common collections
                collections_migration_list = [
                    f"kv_trackme_{component}_tenant_{tenant_id}",
                    f"kv_trackme_{component}_priority_tenant_{tenant_id}",
                    f"kv_trackme_{component}_tags_tenant_{tenant_id}",
                    f"kv_trackme_{component}_sla_tenant_{tenant_id}",
                ]

                # Only these components have Outliers KV collections
                if component in ("dsm", "dhm", "flx", "wlk"):
                    collections_migration_list.append(
                        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}",
                    )
                    collections_migration_list.append(
                        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}",
                    )

                # splk-dsm specific
                if component in ("dsm"):
                    collections_migration_list.append(
                        f"kv_trackme_{component}_data_sampling_tenant_{tenant_id}"
                    )

            else:
                collections_migration_list = [
                    f"kv_trackme_{component}_tenant_{tenant_id}",
                ]

            get_effective_logger().info(f'collections_migration_list="{collections_migration_list}"')

            for collection_name in collections_migration_list:

                # entities KV collection
                collection = service.kvstore[collection_name]

                # created_records_key
                created_records_key = []

                # get records
                collection_records, collection_keys, collection_dict = (
                    get_full_kv_collection(collection, collection_name)
                )

                # for each record
                for record in collection_records:

                    object_value = record.get("object")
                    key_value = record.get("_key")

                    # create the new key using sha256
                    new_key_value = hashlib.sha256(
                        object_value.encode("utf-8")
                    ).hexdigest()

                    # only if required
                    if (
                        key_value != new_key_value
                        and new_key_value not in created_records_key
                    ):

                        record_removed = False
                        try:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2099, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", key_value="{key_value}", new_key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                            )
                            # Remove the record
                            collection.data.delete(json.dumps({"_key": key_value}))
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2099, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", successfully removed record with object_value="{object_value}", key_value="{key_value}", new_key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                            )
                            record_removed = True

                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2099, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", failed to remove the record, key_value="{key_value}", exception="{str(e)}"'
                            )

                        if record_removed:
                            # insert a new record with the replaced key
                            record["_key"] = new_key_value
                            try:
                                collection.data.insert(json.dumps(record))
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2099, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", successfully inserted the new record, key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                                )
                                created_records_key.append(new_key_value)
                            except Exception as e:
                                get_effective_logger().error(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2099, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", failed to insert the new record, key_value="{new_key_value}", exception="{str(e)}", record="{json.dumps(record, indent=2)}"'
                                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2099, procedure terminated'
    )
    return True


"""
In this function:
- Update hybrid trackers to include the object_category option when calling the streaming custom command trackmesplkgetflipping
- Update any hybrid tracker that would be using an md5 approach to calculate the expected hash for TrackMe's object and would have been created before the migration to sha256
- Data Sampling events recognition engine v2 migration (delete existing schedule report and re-create with new search)
- The migration of TrackMe 2.0.98 extended tags for all components, but splk-mhm was forgotten
"""


def trackme_schema_upgrade_2100(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2100, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update hybrid trackers to include the object_category option when calling the streaming custom command trackmesplkgetflipping
        # Update any hybrid tracker that would be using an md5 approach to calculate the expected hash for TrackMe's object and would have been created before the migration to sha256
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_wrapper_to_process = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:

                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = json.loads(tracker_record.get("knowledge_objects"))

                tracker_reports = tracker_kos.get("reports")

                for tracker_report in tracker_reports:
                    if "_wrapper_" in tracker_report:
                        trackers_wrapper_to_process.append(tracker_report)

            # loop through wrapper reports
            for tracker_name in trackers_wrapper_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # calculate the current sha256 hash of tracker_current_search, we will use this information to define if the tracker needs to be updated
                # after the modifications
                tracker_current_search_hash = hashlib.sha256(
                    tracker_current_search.encode("utf-8")
                ).hexdigest()

                # in tracker_current_search, replace the sentence:
                # trackmesplkgetflipping tenant_id=
                # with:
                # trackmesplkgetflipping object_category=spl-<component> tenant_id=

                tracker_new_search = tracker_current_search.replace(
                    f'trackmesplkgetflipping tenant_id="{tenant_id}"',
                    f'trackmesplkgetflipping object_category="splk-{component}" tenant_id="{tenant_id}"',
                )

                # in tracker_current_search, replace any usage of the md5 function with the sha256 function, this can be detected and replaced with:
                # md5(
                # with:
                # sha256(

                tracker_new_search = tracker_new_search.replace("md5(", "sha256(")

                # calculate the new sha256 hash of tracker_new_search
                tracker_new_search_hash = hashlib.sha256(
                    tracker_new_search.encode("utf-8")
                ).hexdigest()

                # if hashes are the name, generate a logging info message as the report does not need to be updated
                if tracker_current_search_hash == tracker_new_search_hash:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search_hash="{tracker_current_search_hash}", tracker_new_search_hash="{tracker_new_search_hash}", tracker_current_search="{tracker_current_search}", tracker_new_search="{tracker_new_search}", tracker does not need to be updated'
                    )

                else:
                    # update the search definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": tracker_name,
                        "report_search": tracker_new_search,
                        "earliest_time": tracker_current_earliest_time,
                        "latest_time": tracker_current_latest_time,
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                        )

        #
        # Data Sampling events recognition engine v2 migration: delete and re-create the report
        #

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:

            # purge the current KVstore records for sampling

            # Define the query
            search = f"| outputlookup trackme_dsm_data_sampling_tenant_{tenant_id}"

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", purge data sampling collection, search="{search}"'
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

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", data sampling collection was purged.'
                )

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to execute the data sampling collection purge, exception="{str(e)}"'
                )

            # boolean to act depending on the report deletion
            report_deleted = False

            # report name
            report_name = f"trackme_dsm_data_sampling_tracker_tenant_{tenant_id}"

            # delete the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", delete report has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully deleted report, report="{report_name}"'
                    )
                    report_deleted = True

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to delete the report, report="{report_name}", exception="{str(e)}"'
                )

            # create the report
            if report_deleted:

                report_search = f'| trackmesamplingexecutor tenant_id="{tenant_id}"'
                report_properties = {
                    "description": "TrackMe DSM Data Sampling tracker",
                    "is_scheduled": True,
                    "schedule_window": "5",
                    "cron_schedule": "*/20 * * * *",
                    "dispatch.earliest_time": "-24h",
                    "dispatch.latest_time": "-4h",
                }
                report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                    "report_search": report_search,
                    "report_properties": report_properties,
                    "report_acl": report_acl,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                    )

            #
            # update collection transforms
            #

            # set
            transform_name = f"trackme_dsm_data_sampling_tenant_{tenant_id}"
            collection_name = f"kv_trackme_dsm_data_sampling_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_dsm_data_sampling"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create tags tracker for splk-mhm
        #

        components_to_process = []

        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            #
            # First check if the procedure is required, to do so we will call an endpoint to check if the report exists
            #

            run_procedure = False
            report_name = f"trackme_{component}_tags_tracker_tenant_{tenant_id}"

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/get_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", the expected report does not exist, procedure is required, report="{report_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                    run_procedure = True
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully got report definition, procedure is not required, report="{report_name}"'
                    )
                    run_procedure = False
            except Exception as e:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", the expected report does not exist, procedure is required, report="{report_name}", exception="{str(e)}"'
                )
                run_procedure = True

            # proceed if required
            if run_procedure:

                #
                # update main collection transforms
                #

                # set
                transform_name = f"trackme_{component}_tenant_{tenant_id}"
                collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
                transform_fields = collections_dict[f"trackme_{component}"]
                ko_acl = {
                    "owner": vtenant_record.get("tenant_owner"),
                    "sharing": trackme_default_sharing,
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # delete the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                #
                # Create the tags collection and transforms
                #

                # set
                transform_name = f"trackme_{component}_tags_tenant_{tenant_id}"
                collection_name = f"kv_trackme_{component}_tags_tenant_{tenant_id}"
                transform_fields = collections_dict[f"trackme_{component}_tags"]
                ko_acl = {
                    "owner": vtenant_record.get("tenant_owner"),
                    "sharing": trackme_default_sharing,
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # create the KVstore collection
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
                data = {
                    "tenant_id": tenant_id,
                    "collection_name": collection_name,
                    "collection_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                kvstore_created = False
                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                        )
                        kvstore_created = True
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                    )

                # continue
                if kvstore_created:

                    # create the transform
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                    data = {
                        "tenant_id": tenant_id,
                        "transform_name": transform_name,
                        "transform_fields": transform_fields,
                        "collection_name": collection_name,
                        "transform_acl": ko_acl,
                        "owner": vtenant_record.get("tenant_owner"),
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                        )

                #
                # Create the tags policies collection and transforms (for all components)
                #

                # set
                transform_name = f"trackme_{component}_tags_policies_tenant_{tenant_id}"
                collection_name = (
                    f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
                )
                transform_fields = collections_dict[f"trackme_{component}_tags"]
                ko_acl = {
                    "owner": vtenant_record.get("tenant_owner"),
                    "sharing": trackme_default_sharing,
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # create the KVstore collection
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
                data = {
                    "tenant_id": tenant_id,
                    "collection_name": collection_name,
                    "collection_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                kvstore_created = False
                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                        )
                        kvstore_created = True
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                    )

                # continue
                if kvstore_created:

                    # create the transform
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                    data = {
                        "tenant_id": tenant_id,
                        "transform_name": transform_name,
                        "transform_fields": transform_fields,
                        "collection_name": collection_name,
                        "transform_acl": ko_acl,
                        "owner": vtenant_record.get("tenant_owner"),
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                        )

                #
                # Create the report tracker (not for dsm, as it already exists)
                #

                report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": tenant_roles_write_perms,
                    "perms.read": tenant_roles_read_perms,
                }

                # create the tracker report
                report_name = f"trackme_{component}_tags_tracker_tenant_{tenant_id}"
                report_search = (
                    f'| trackmesplktags tenant_id="{tenant_id}" component="{component}"'
                )
                report_properties = {
                    "description": f"This scheduled report applies and maintains tags policies for the splk-{component} component",
                    "is_scheduled": True,
                    "cron_schedule": "*/15 * * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }

                # create the report
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                    "report_search": report_search,
                    "report_properties": report_properties,
                    "report_acl": report_acl,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2100, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                    )

                # Execute tags update now
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/splk_tag_policies/write/tag_policies_apply'
                post_data = {
                    "tenant_id": tenant_id,
                    "component": component,
                }

                # update the account
                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(post_data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2100, tags apply operation has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2100, tags apply operation was executed successfully, response.status_code="{response.status_code}", response="{json.dumps(response.json(), indent=2)}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2100, tags apply operation has failed, exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2100, procedure terminated'
    )
    return True


"""
In this function:
- For Flex Object tenants, update the inactive_entities_tracker to remove an unused option and define increased default value to auto purge.
"""


def trackme_schema_upgrade_2101(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2101, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Adaptive flx inactive entities tracker
        #

        components_to_process = []
        if (
            vtenant_record.get("tenant_flx_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("flx")

        for component in components_to_process:

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with Flex inactive entities tracker update'
            )

            # report name
            tracker_name = f"trackme_flx_inactive_entities_tracker_tenant_{tenant_id}"

            # get the current search definition
            try:
                tracker_current = service.saved_searches[tracker_name]
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                )
                continue

            tracker_current_search = tracker_current.content.get("search")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
            )

            # add our new parameter
            tracker_new_search = f'| trackmesplkflxinactiveinspector tenant_id="{tenant_id}" register_component="True" report="{tracker_name}" max_days_since_inactivity_before_purge=30'

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_name,
                "report_search": tracker_new_search,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2101, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2101, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2101, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2101, procedure terminated'
    )
    return True


"""
In this function:
- Update tenant allowlist transforms definition
- Update the Virtual Tenant account with the sampling option
"""


def trackme_schema_upgrade_2102(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2102, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update allowlist transforms definition (for feeds components only)
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # select components
        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            # set
            transform_name = f"trackme_{component}_allowlist_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_allowlist"]
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2102, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2102, procedure terminated'
    )
    return True


"""
In this function:
- Create the allowlist collections for splk-flx/wlk
- Update transforms definition for lagging classes
"""


def trackme_schema_upgrade_2104(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2104, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # allowlist extension to splk-flx and splk-wlk
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # Create the allowlist collection and transforms
            #

            # set
            transform_name = f"trackme_{component}_allowlist_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_allowlist"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # continue
            if kvstore_created:

                # create the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # lagging class transforms update
        #

        # select components
        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")

        for component in components_to_process:

            # set

            if component in ("dsm", "dhm"):
                transform_name = f"trackme_common_lagging_classes_tenant_{tenant_id}"
                collection_name = (
                    f"kv_trackme_common_lagging_classes_tenant_{tenant_id}"
                )
                transform_fields = collections_dict[f"trackme_common_lagging_classes"]

            elif component in ("mhm"):
                transform_name = f"trackme_mhm_lagging_classes_tenant_{tenant_id}"
                collection_name = f"kv_trackme_mhm_lagging_classes_tenant_{tenant_id}"
                transform_fields = collections_dict[f"trackme_mhm_lagging_classes"]

            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": transform_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2104, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2104, procedure terminated'
    )
    return True


"""
In this function:
 - Address defect for splk-wlk the transition from md5 hashlib to sha256 for FIPS that was processed in 2.0.99
 """


def trackme_schema_upgrade_2105(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2105, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # md5 to sha256 migration
        #

        tenant_id = vtenant_record.get("tenant_id")

        components_to_process = []

        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # migrate records from md5 to sha256
            #

            # common collections
            collections_migration_list = [
                f"kv_trackme_{component}_tenant_{tenant_id}",
                f"kv_trackme_{component}_priority_tenant_{tenant_id}",
                f"kv_trackme_{component}_tags_tenant_{tenant_id}",
                f"kv_trackme_{component}_sla_tenant_{tenant_id}",
            ]

            # Only these components have Outliers KV collections
            if component in ("wlk"):
                collections_migration_list.append(
                    f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}",
                )
                collections_migration_list.append(
                    f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}",
                )

            get_effective_logger().info(f'collections_migration_list="{collections_migration_list}"')

            for collection_name in collections_migration_list:

                # entities KV collection
                collection = service.kvstore[collection_name]

                # created_records_key
                created_records_key = []

                # get records
                collection_records, collection_keys, collection_dict = (
                    get_full_kv_collection(collection, collection_name)
                )

                # for each record
                for record in collection_records:

                    object_value = record.get("object")
                    key_value = record.get("_key")

                    # create the new key using sha256
                    new_key_value = hashlib.sha256(
                        object_value.encode("utf-8")
                    ).hexdigest()

                    # only if required
                    if (
                        key_value != new_key_value
                        and new_key_value not in created_records_key
                    ):

                        record_removed = False
                        try:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2105, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", key_value="{key_value}", new_key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                            )
                            # Remove the record
                            collection.data.delete(json.dumps({"_key": key_value}))
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2105, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", successfully removed record with object_value="{object_value}", key_value="{key_value}", new_key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                            )
                            record_removed = True

                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2105, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", failed to remove the record, key_value="{key_value}", exception="{str(e)}"'
                            )

                        if record_removed:
                            # insert a new record with the replaced key
                            record["_key"] = new_key_value
                            try:
                                collection.data.insert(json.dumps(record))
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2105, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", successfully inserted the new record, key_value="{new_key_value}", record="{json.dumps(record, indent=2)}"'
                                )
                                created_records_key.append(new_key_value)
                            except Exception as e:
                                get_effective_logger().error(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, subcontext="records-migration", schema migration 2105, tenant_id="{tenant_id}", component="{component}", collection="{collection_name}", migrating record with object_value="{object_value}", failed to insert the new record, key_value="{new_key_value}", exception="{str(e)}", record="{json.dumps(record, indent=2)}"'
                                )

            #
            # Migrate trackers (only for splk-wlk)
            #

            # check components and add accordingly
            if vtenant_record.get("tenant_wlk_enabled") == 1:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", processing with the schema upgrade'
                )

                # retrieve the list of scheduler reports to be processed
                collection_trackers_name = (
                    f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
                )
                collection_trackers = service.kvstore[collection_trackers_name]

                trackers_dict = {}

                trackers_to_process = []
                trackers_to_process_kos = []

                # get records from the KVstore
                trackers_records = collection_trackers.data.query()

                for tracker_record in trackers_records:
                    tracker_name = tracker_record.get("tracker_name")
                    tracker_kos = tracker_record.get("knowledge_objects")
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)
                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

                # loop through the trackers
                for tracker_shortname in trackers_to_process:
                    tracker_name = f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"

                    tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                    # get the current search definition
                    try:
                        tracker_current = service.saved_searches[tracker_name]
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                        )
                        continue

                    tracker_current_search = tracker_current.content.get("search")
                    tracker_account = tracker_kos["properties"][0]["account"]

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                    )

                    # in tracker_current_search, replace any presence of md5 by sha256

                    try:
                        tracker_new_search = re.sub(
                            r"md5\(([^)]+)\)",
                            r"sha256(\1)",
                            tracker_current_search,
                        )

                        # update the search definition
                        tracker_current.update(search=tracker_new_search)

                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, the tracker was updated successfully, new_search="{tracker_new_search}"'
                        )

                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, failed to update the tracker, exception="{str(e)}"'
                        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2105, procedure terminated'
    )
    return True


"""
In this function:
- Update maintransforms definition for splk-flx
"""


def trackme_schema_upgrade_2107(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2107, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # update transforms definition for splk-flx
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2107, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2107, procedure terminated'
    )
    return True


"""
In this function:
- Update any existing Splunk Remote account preferences to include default values
"""


def trackme_schema_upgrade_2108(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2108, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2108, procedure terminated'
    )
    return True


"""
In this function:
- Update all trackers to remove explicit calls to earliest and latest arguments, and add explicit call to alert_no_results
"""


def trackme_schema_upgrade_2109(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2109, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update tracker main searches to remove explicit earliest/latest, and add explicit alert_no_results
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            # A list to store trackers to be processed
            trackers_to_process = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:

                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = json.loads(tracker_record.get("knowledge_objects"))
                tracker_reports = tracker_kos.get("reports")

                for tracker_report in tracker_reports:
                    # exclude _abstract _wrapper trackers
                    if (
                        not "_abstract_" in tracker_report
                        and not "_wrapper_" in tracker_report
                    ):
                        trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace the sentence:
                #  earliest=<anything but space> latest=<anything but space>
                # with:
                #  alert_no_results=True

                tracker_new_search = re.sub(
                    r"earliest=[^\s]+ latest=[^\s]+",
                    r"alert_no_results=True",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2109, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2109, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2109, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2109, procedure terminated'
    )
    return True


"""
In this function:
- Update all components main transforms definition to include priority_reason
- Update all trackers to handle schedule_window inconsistencies
- Create delayed entities inspector collections for dsm and dhm
- Create delayed entities inspector trackers for dsm and dhm
- Create last seen activity collection for flx
- Update the adaptive delay report to add the new option max_sla_percentage
"""


def trackme_schema_upgrade_2110(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2110, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update main transforms
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update alerts
        #

        try:
            alert_kos = json.loads(vtenant_record.get("tenant_alert_objects"))
            alert_reports = alert_kos.get("alerts")
        except Exception as e:
            alert_reports = []

        # get records from the KVstore
        for alert_name in alert_reports:

            # get the current search definition
            alert_current = None
            try:
                alert_current = service.saved_searches[alert_name]
            except Exception as e:
                alert_current = None

            if alert_current:
                alert_current_search = alert_current.content.get("search")
                alert_current_search = alert_current.content.get("search")
                alert_current_earliest_time = alert_current.content.get(
                    "dispatch.earliest_time"
                )
                alert_current_latest_time = alert_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", alert_current_search="{alert_current_search}"'
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": alert_name,
                    "report_search": alert_current_search,
                    "earliest_time": alert_current_earliest_time,
                    "latest_time": alert_current_latest_time,
                    "schedule_window": "5",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", update report definition has failed, report="{alert_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully updated report definition, report="{alert_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to update the report definition, report="{alert_name}", exception="{str(e)}"'
                    )

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                # exclude _abstract _wrapper trackers
                if (
                    not "_abstract_" in tracker_report
                    and not "_wrapper_" in tracker_report
                ):
                    trackers_to_process.append(tracker_report)

            # for splk-dsm only, add trackme_dsm_data_sampling_tracker_tenant_<tenant_id>, trackme_dsm_shared_elastic_tracker_tenant_<tenant_id>
            if component == "dsm":
                trackers_to_process.append(
                    f"trackme_dsm_data_sampling_tracker_tenant_{tenant_id}"
                )
                trackers_to_process.append(
                    f"trackme_dsm_shared_elastic_tracker_tenant_{tenant_id}"
                )

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_current_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                    "schedule_window": "5",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # Create Kvstore collections and transforms for delayed entities inspector
        #

        components_to_process = []

        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dhm")

        for component in components_to_process:

            # set
            transform_name = (
                f"trackme_{component}_delayed_entities_inspector_tenant_{tenant_id}"
            )
            collection_name = (
                f"kv_trackme_{component}_delayed_entities_inspector_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[
                f"trackme_{component}_delayed_entities_inspector"
            ]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created the collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created the transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the transform, transform="{transform_name}", exception="{str(e)}"'
                )

            #
            # Create the adaptive delay tracker
            #

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": trackme_default_sharing,
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            # create the wrapper
            report_name = f"trackme_{component}_delayed_entities_inspector_tracker_tenant_{tenant_id}"
            report_search = f'| trackmesplkfeedsdelayedinspector tenant_id="{tenant_id}" component="{component}" max_runtime=900'
            report_properties = {
                "description": f"This scheduled report manages delayed entities in the {component} component",
                "is_scheduled": True,
                "cron_schedule": "*/20 * * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # create the report
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

        #
        # Create Kvstore collections and transforms for last seen activity in splk-flx
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            # set
            transform_name = (
                f"trackme_{component}_last_seen_activity_tenant_{tenant_id}"
            )
            collection_name = (
                f"kv_trackme_{component}_last_seen_activity_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[
                f"trackme_{component}_last_seen_activity"
            ]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created the collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully created the transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to create the transform, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Adaptive trackers
        #

        components_to_process = []
        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            components_to_process.append("dhm")

        for component in components_to_process:
            #
            # Update the adaptive delay tracker
            #

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="{component}", processing with adaptive delay tracker update'
            )

            # report name
            tracker_name = (
                f"trackme_{component}_adaptive_delay_tracker_tenant_{tenant_id}"
            )

            # get the current search definition
            try:
                tracker_current = service.saved_searches[tracker_name]
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                )
                continue

            tracker_current_search = tracker_current.content.get("search")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
            )

            # add our new parameter
            tracker_new_search = f"{tracker_current_search} max_sla_percentage=90"

            # update the search definition
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": tracker_name,
                "report_search": tracker_new_search,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2110, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2110, procedure terminated'
    )
    return True


"""
In this function:
- Update all components main transforms definition
- Update all trackers to report the list of objects it manages, for the purpose of the handler events component and the deprecation of the macro trackme_auto_disablement_period
- Create the new collection and transform for stateful alerting
- Create the new collection and transform for stateful alerting charts
- Create the new collection and transform for SLA notifications
- Update Splunk Cloud Workload SVC trackers to switch to the new index
- Update all Flex Trackers related to Splunk Cloud SVC usage to switch to the new index
"""


def trackme_schema_upgrade_2111(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2111, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update main transforms
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                # include only _wrapper trackers
                if "_wrapper_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", failed to get the tracker definition, tracker="{tracker_name}", exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace the sentence:
                # stats count as report_entities_count by tenant_id
                # with:
                # stats count as report_entities_count, values(object) as report_objects_list by tenant_id

                tracker_new_search = re.sub(
                    r"stats count as report_entities_count by tenant_id",
                    r"stats count as report_entities_count, values(object) as report_objects_list by tenant_id",
                    tracker_current_search,
                )

                # deprecation of the macro trackme_auto_disablement_period

                # in tracker_new_search, remove the following, if present:
                # | eval monitored_state=if(metric_last_time_seen<=`trackme_auto_disablement_period`, "disabled", monitored_state)
                # | eval monitored_state=if(metric_last_time_seen<=`trackme_auto_disablement_period`, \"disabled\", monitored_state)
                # | eval monitored_state=if(data_last_time_seen<=`trackme_auto_disablement_period`, "disabled", monitored_state)
                # | eval monitored_state=if(data_last_time_seen<=`trackme_auto_disablement_period`, \"disabled\", monitored_state)
                tracker_new_search = re.sub(
                    r"\| eval monitored_state=if\(metric_last_time_seen<=`trackme_auto_disablement_period`, \"disabled\", monitored_state\)",
                    "",
                    tracker_new_search,
                )
                tracker_new_search = re.sub(
                    r"\| eval monitored_state=if\(data_last_time_seen<=`trackme_auto_disablement_period`, \"disabled\", monitored_state\)",
                    "",
                    tracker_new_search,
                )
                tracker_new_search = re.sub(
                    r"\| eval monitored_state=if\(metric_last_time_seen<=`trackme_auto_disablement_period`, \\\"disabled\\\", monitored_state\)",
                    "",
                    tracker_new_search,
                )
                tracker_new_search = re.sub(
                    r"\| eval monitored_state=if\(data_last_time_seen<=`trackme_auto_disablement_period`, \\\"disabled\\\", monitored_state\)",
                    "",
                    tracker_new_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # Create the new collection and transform for stateful alerting
        #

        # set
        transform_name = f"trackme_stateful_alerting_tenant_{tenant_id}"
        collection_name = f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_stateful_alerting"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # Only continue if successful
        #

        if kvstore_created:

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create the new collection and transform for stateful alerting charts
        #

        # set
        transform_name = f"trackme_stateful_alerting_charts_tenant_{tenant_id}"
        collection_name = f"kv_trackme_stateful_alerting_charts_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_stateful_alerting_charts"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # Only continue if successful
        #

        if kvstore_created:

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create the new collection and transform for SLA notifications
        #

        # set
        transform_name = f"trackme_{component}_sla_notifications_tenant_{tenant_id}"
        collection_name = f"kv_trackme_{component}_sla_notifications_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_{component}_sla_notifications"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # Only continue if successful
        #

        if kvstore_created:

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # splk-wlk: Update Workload SVC trackers to switch to the new index
        #

        if (
            vtenant_record.get("tenant_wlk_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="wlk", processing with Workload tracker updates'
            )

            #
            # Trackers updates
            #

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_dict = {}
            trackers_to_process = []
            trackers_to_process_kos = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:
                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = tracker_record.get("knowledge_objects")

                # if the tracker_name starts by scheduler_
                if re.search("^splunkcloud_", tracker_name):
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)

                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

            # loop through the trackers (wrapper)
            for tracker_shortname in trackers_to_process:
                tracker_name = (
                    f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"
                )

                tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to retrieve the current search definition, tracker_name="{tracker_name}", exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_account = tracker_kos["properties"][0]["account"]
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                )

                # in tracker_current_search, replace the sentence:
                #  index=summary
                # with:
                #  (index=_cmc_summary OR index=summary)

                tracker_new_search = re.sub(
                    r"index=summary",
                    r"(index=_cmc_summary OR index=summary)",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # splk-flx: Update Flex Object trackers that would track SVC usage
        #

        if (
            vtenant_record.get("tenant_flx_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="flx", processing with Flex Objects tracker updates'
            )

            component = "flx"

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                if "_wrapper_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to retrieve the current search definition, tracker_name="{tracker_name}", exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                # get the search definition, if it contains index=summary and splunk-svc or splunk-storage-summary, process, otherwise skip
                if re.search(
                    "index=summary.*splunk-svc", tracker_current_search
                ) or re.search(
                    "index=summary.*splunk-storage-summary", tracker_current_search
                ):
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, processing Flex tracker, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, skipping Flex tracker, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                    )
                    continue

                # in tracker_current_search, replace the sentence:
                #  index=summary
                # with:
                #  (index=_cmc_summary OR index=summary)

                tracker_new_search = re.sub(
                    r"index=summary",
                    r"(index=_cmc_summary OR index=summary)",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                    "schedule_window": "5",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # Verify and update the Virtual Tenant account configuration for the delayed entities inspector
        #

        url = f'{reqinfo["server_rest_uri"]}/servicesNS/nobody/trackme/trackme_vtenants/{tenant_id}'
        vtenant_data = {}

        try:
            # Get current vtenant account configuration
            response = requests.get(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                verify=False,
                params={"output_mode": "json"},
                timeout=600,
            )
            if response.status_code in (200, 201, 204):

                get_effective_logger().info(f"successfully retrieved vtenant configuration")
                vtenant_data_json = response.json()
                vtenant_data_current = vtenant_data_json["entry"][0]["content"]

                # Start with the current configuration and add missing keys from the default config
                # We keep all keys from the current configuration
                for key, value in vtenant_data_current.items():
                    if key in vtenant_account_default:
                        vtenant_data[key] = value

                # before merging with the default config, check if any key is missing
                for key in vtenant_account_default.keys():
                    if key not in vtenant_data:
                        update_is_required = True

                # Merge with default config, only adding missing default keys
                for key, value in vtenant_account_default.items():
                    if key not in vtenant_data:
                        vtenant_data[key] = value

                # Finally, ensures that each key in vtenant_data exists in vtenant_account_default, otherwise drop it
                vtenant_data = {
                    key: value
                    for key, value in vtenant_data.items()
                    if key in vtenant_account_default
                }

            else:
                error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to retrieve vtenant configuration, status_code={response.status_code}'
                get_effective_logger().error(error_msg)

        except Exception as e:
            error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to retrieve vtenant configuration, exception={str(e)}'
            get_effective_logger().error(error_msg)

        # get current values
        if vtenant_data:

            # current values from the vtenant account configuration
            splk_feeds_delayed_inspector_24hours_range_min_sec = int(
                vtenant_data.get("splk_feeds_delayed_inspector_24hours_range_min_sec")
            )
            splk_feeds_delayed_inspector_7days_range_min_sec = int(
                vtenant_data.get("splk_feeds_delayed_inspector_7days_range_min_sec")
            )
            splk_feeds_delayed_inspector_until_disabled_range_min_sec = int(
                vtenant_data.get(
                    "splk_feeds_delayed_inspector_until_disabled_range_min_sec"
                )
            )

            # get system default values
            default_splk_feeds_delayed_inspector_24hours_range_min_sec = int(
                vtenant_account_default.get(
                    "splk_feeds_delayed_inspector_24hours_range_min_sec"
                )
            )
            default_splk_feeds_delayed_inspector_7days_range_min_sec = int(
                vtenant_account_default.get(
                    "splk_feeds_delayed_inspector_7days_range_min_sec"
                )
            )
            default_splk_feeds_delayed_inspector_until_disabled_range_min_sec = int(
                vtenant_account_default.get(
                    "splk_feeds_delayed_inspector_until_disabled_range_min_sec"
                )
            )

            # init vetenant_update_data
            vtenant_update_data = {}

            # for each, if the current value is lower than the default value, update the value
            if (
                splk_feeds_delayed_inspector_24hours_range_min_sec
                < default_splk_feeds_delayed_inspector_24hours_range_min_sec
            ):
                vtenant_update_data[
                    "splk_feeds_delayed_inspector_24hours_range_min_sec"
                ] = default_splk_feeds_delayed_inspector_24hours_range_min_sec
            if (
                splk_feeds_delayed_inspector_7days_range_min_sec
                < default_splk_feeds_delayed_inspector_7days_range_min_sec
            ):
                vtenant_update_data[
                    "splk_feeds_delayed_inspector_7days_range_min_sec"
                ] = default_splk_feeds_delayed_inspector_7days_range_min_sec
            if (
                splk_feeds_delayed_inspector_until_disabled_range_min_sec
                < default_splk_feeds_delayed_inspector_until_disabled_range_min_sec
            ):
                vtenant_update_data[
                    "splk_feeds_delayed_inspector_until_disabled_range_min_sec"
                ] = default_splk_feeds_delayed_inspector_until_disabled_range_min_sec

            # if vtenant_update_data is not empty, update the vtenant account configuration
            if vtenant_update_data:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", processing with vtenant account configuration updates, parameters="{json.dumps(vtenant_update_data, indent=2)}"'
                )
                try:
                    update_vtenant_configuration(
                        reqinfo,
                        task_name,
                        task_instance_id,
                        tenant_id,
                        updated_vtenant_data=vtenant_update_data,
                    )
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", successfully updated vtenant account configuration'
                    )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2111, tenant_id="{tenant_id}", failed to update vtenant account configuration, exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2111, procedure terminated'
    )
    return True


"""
In this function:
- Update StateFul alerts to include the trackme:state event logic
"""


def trackme_schema_upgrade_2116(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2116, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update StateFul alerts
        #

        try:
            alert_kos = json.loads(vtenant_record.get("tenant_alert_objects"))
            alert_reports = alert_kos.get("alerts")
        except Exception as e:
            alert_reports = []

        # get records from the KVstore
        for alert_name in alert_reports:

            # get the current search definition
            alert_current = None
            try:
                alert_current = service.saved_searches[alert_name]
            except Exception as e:
                alert_current = None

            # alert_is_stateful boolean
            alert_is_stateful = False

            if alert_current:
                alert_current_search = alert_current.content.get("search")
                alert_current_earliest_time = alert_current.content.get(
                    "dispatch.earliest_time"
                )
                alert_current_latest_time = alert_current.content.get(
                    "dispatch.latest_time"
                )

                # define if the alert is stateful, check in the search definition if we can find:
                # (sourcetype=trackme:flip) and (sourcetype=trackme:sla_breaches) and trackme_notable_idx
                if (
                    re.search(
                        r"(sourcetype=trackme:flip)",
                        alert_current_search,
                    )
                    and re.search(
                        r"(sourcetype=trackme:sla_breaches)",
                        alert_current_search,
                    )
                    and re.search(
                        r"(trackme_notable_idx)",
                        alert_current_search,
                    )
                ):
                    alert_is_stateful = True

                # do not process if the alert is not stateful
                if not alert_is_stateful:
                    continue

                # set the new search definition
                new_search_segment = f'( (`trackme_idx({tenant_id})` (sourcetype=trackme:state) tenant_id="{tenant_id}" object_category="*" object_state!="green") NOT [ | inputlookup trackme_stateful_alerting_tenant_{tenant_id} where (alert_status="opened" OR alert_status="updated") | eval _time=mtime | stats latest(alert_status) as alert_status by object_id | fields object_id | rename object_id as key | format | return $search ] ) OR '
                new_alert_search = f"{new_search_segment} {alert_current_search}"

                # update the search definition
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", alert_current_search="{alert_current_search}"'
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": alert_name,
                    "report_search": new_alert_search,
                    "earliest_time": alert_current_earliest_time,
                    "latest_time": alert_current_latest_time,
                    "schedule_window": "5",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration {target_version}, tenant_id="{tenant_id}", update report definition has failed, report="{alert_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration {target_version}, tenant_id="{tenant_id}", successfully updated report definition, report="{alert_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration {target_version}, tenant_id="{tenant_id}", failed to update the report definition, report="{alert_name}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration {target_version}, procedure terminated'
    )
    return True


"""
In this function:
- Create thresholds collection for flx
- Create disruption queue collection (common)
"""


def trackme_schema_upgrade_2118(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2118, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Create Kvstore collections and transforms for thresholds management in splk-flx
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            # set
            transform_name = f"trackme_{component}_thresholds_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_thresholds_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_thresholds"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", failed to create the collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", successfully created the collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", failed to create the collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", failed to create the transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", successfully created the transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", failed to create the transform, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create the common collection and transform for disruption queue
        #

        # set
        transform_name = f"trackme_common_disruption_queue_tenant_{tenant_id}"
        collection_name = f"kv_trackme_common_disruption_queue_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_common_disruption_queue"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # Only continue if successful
        #

        if kvstore_created:

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2118, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2118, procedure terminated'
    )
    return True


"""
In this function:
- Update stateful alerting definition for the Virtual Tenant
"""


def trackme_schema_upgrade_2119(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2119, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # update transforms definition for the Virtual Tenant
        #

        #
        # update main collection transforms
        #

        # set
        transform_name = f"trackme_stateful_alerting_tenant_{tenant_id}"
        collection_name = f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_stateful_alerting"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # delete the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

        # create the transform
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
        data = {
            "tenant_id": tenant_id,
            "transform_name": transform_name,
            "transform_fields": transform_fields,
            "collection_name": collection_name,
            "transform_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2119, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2119, procedure terminated'
    )
    return True


"""
In this function:
- Update registered TrackMe alerts to call trackme_apply_maintenance_mode_v2 instead of trackme_apply_maintenance_mode
"""


def trackme_schema_upgrade_2121(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2121, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update alerts
        #

        # get alert object from field tenant_alert_objects
        alert_objects = vtenant_record.get("tenant_alert_objects", None)

        # check if we have alert objects
        if alert_objects:

            # load the alert objects as a json object
            try:
                alert_objects = json.loads(alert_objects)
            except Exception as e:
                # log alerts to be updated
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", no alerts found for update.'
                )

            # get list of alerts
            alerts_list = alert_objects.get("alerts", [])

            # for each alert
            for alert_name in alerts_list:

                alert_current = None
                try:
                    alert_current = service.saved_searches[alert_name]
                except Exception as e:
                    pass

                if alert_current:
                    alert_current_search = alert_current.content.get("search")
                    alert_current_earliest_time = alert_current.content.get(
                        "dispatch.earliest_time"
                    )
                    alert_current_latest_time = alert_current.content.get(
                        "dispatch.latest_time"
                    )

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", alert_current_search="{alert_current_search}"'
                    )

                    """
                    in alert_current_search, replace the following sentence using regex:

                    `trackme_apply_maintenance_mode`

                    by:

                    `trackme_apply_maintenance_mode_v2`

                    """

                    alert_new_search = re.sub(
                        r"`trackme_apply_maintenance_mode`",
                        r"`trackme_apply_maintenance_mode_v2`",
                        alert_current_search,
                    )

                    # update the alert definition
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                    data = {
                        "tenant_id": tenant_id,
                        "report_name": alert_name,
                        "report_search": alert_new_search,
                        "earliest_time": alert_current_earliest_time,
                        "latest_time": alert_current_latest_time,
                    }

                    try:
                        response = requests.post(
                            url,
                            headers={
                                "Authorization": f'Splunk {reqinfo["session_key"]}'
                            },
                            data=json.dumps(data),
                            verify=False,
                            timeout=600,
                        )
                        if response.status_code not in (200, 201, 202, 204):
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2121, tenant_id="{tenant_id}", update alert definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                            )
                        else:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2121, tenant_id="{tenant_id}", successfully updated alert definition, alert="{alert_name}"'
                            )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2121, tenant_id="{tenant_id}", failed to update the alert definition, report="{alert_name}", exception="{str(e)}"'
                        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2121, procedure terminated'
    )
    return True


"""
In this function:
- Update Vtenant central collection for the new splk-fqm components to be set as explicitly disabled in existint tenants
"""


def trackme_schema_upgrade_2122(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2121, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        # init the fqm component to be disabled
        vtenant_record["tenant_fqm_enabled"] = 0

        # update
        try:
            collection_vtenants.data.update(
                str(vtenant_key), json.dumps(vtenant_record)
            )
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2122, Virtual Tenant updated successfully, result="{json.dumps(vtenant_record, indent=2)}"'
            )

        except Exception as e:
            error_msg = f'task="{task_name}", task_instance_id={task_instance_id}, function trackme_schema_upgrade_2122, failed to update the Virtual Tenant record, exception="{str(e)}"'
            get_effective_logger().error(error_msg)

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2222, procedure terminated'
    )
    return True


"""
In this function:
- Update fqm monitor trackers to include the trackme_fqm_get_description_extended macro
"""

def trackme_schema_upgrade_2123(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2123, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        for component in components_to_process:

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                # include only _wrapper trackers
                if "fqm_monitor" in tracker_report and "_wrapper_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace the sentence:
                # | stats values(description) as description
                # with:
                # | `trackme_fqm_get_description_extended` | stats values(description) as description

                tracker_new_search = re.sub(
                    r"\| stats values\(description\) as description",
                    r"| `trackme_fqm_get_description_extended`\n| stats values(description) as description",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2123, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2123, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2123, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2123, procedure terminated'
    )
    return True


"""
In this function:
- Update fqm trackers to include sort 0 _time to force processing on the search heads
"""

def trackme_schema_upgrade_2126(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2126, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        for component in components_to_process:

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                # include only _wrapper trackers
                if "_wrapper_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace:
                # | fields *
                # with:
                # | fields * | sort 0 _time

                tracker_new_search = re.sub(
                    r"\| fields \*",
                    r"| fields * | sort 0 _time",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2126, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2126, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2126, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2126, procedure terminated'
    )
    return True


"""
In this function:
- Update fqm monitor wrappers to include the call to trackme_fqm_get_description_extended
"""

def trackme_schema_upgrade_2128(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2128, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        for component in components_to_process:

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                # include only _wrapper trackers
                if "_wrapper_" in tracker_report and "_monitor_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                # do not proceed if the search already calls the macro
                if "trackme_fqm_get_description_extended" in tracker_current_search:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", the search already calls the macro, skipping'
                    )
                    continue

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", component="splk-{component}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                )

                # in tracker_current_search, replace:
                # | stats values(description) as description,
                # with:
                # | `trackme_fqm_get_description_extended`
                # | stats values(description) as description,

                tracker_new_search = re.sub(
                    r"\| stats values\(description\) as description,",
                    r"| `trackme_fqm_get_description_extended`\n| stats values(description) as description,",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2128, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2128, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2128, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2128, procedure terminated'
    )
    return True

"""
In this function:
- Fix defect which had led to the duplication of records in the dedicated trackers collection for the flx component
"""

def trackme_schema_upgrade_2130(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2130, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update trackers
        #

        components_to_process = []

        # for all components
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            # Load the dedicated tracker collection
            tracker_collection_name = (
                f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            )
            tracker_collection = service.kvstore[tracker_collection_name]

            # Get existing tracker records from dedicated collection
            existing_tracker_records = tracker_collection.data.query()

            # loop through the records, any record that does not have a value for tracker_id must be removed from the collection
            for tracker_record in existing_tracker_records:
                tracker_key = tracker_record.get("_key")
                tracker_id = tracker_record.get("tracker_id")

                if not tracker_id or len(tracker_id) == 0:
                    try:
                        tracker_collection.data.delete(json.dumps({"_key": tracker_key}))
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2130, tenant_id="{tenant_id}", component="splk-{component}", successfully removed the record {json.dumps(tracker_record, indent=2)} from the KVstore collection {tracker_collection_name}'
                        )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2130, tenant_id="{tenant_id}", component="splk-{component}", failed to remove the record {json.dumps(tracker_record, indent=2)} from the KVstore collection {tracker_collection_name}, exception=\"{str(e)}\"'
                        )

            # Get updated tracker records after removing records without tracker_id
            updated_tracker_records = tracker_collection.data.query()
            
            # Group records by tracker_name to identify duplicates
            tracker_name_groups = {}
            for tracker_record in updated_tracker_records:
                tracker_name = tracker_record.get("tracker_name")
                if tracker_name:
                    if tracker_name not in tracker_name_groups:
                        tracker_name_groups[tracker_name] = []
                    tracker_name_groups[tracker_name].append(tracker_record)
            
            # Remove duplicates based on tracker_name, keeping only the first record for each tracker_name
            for tracker_name, records in tracker_name_groups.items():
                if len(records) > 1:
                    # Keep the first record, remove the rest
                    records_to_remove = records[1:]
                    for record_to_remove in records_to_remove:
                        tracker_key = record_to_remove.get("_key")
                        try:
                            tracker_collection.data.delete(json.dumps({"_key": tracker_key}))
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2130, tenant_id="{tenant_id}", component="splk-{component}", successfully removed duplicate record with tracker_name="{tracker_name}" from the KVstore collection {tracker_collection_name}'
                            )
                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2130, tenant_id="{tenant_id}", component="splk-{component}", failed to remove duplicate record with tracker_name="{tracker_name}" from the KVstore collection {tracker_collection_name}, exception=\"{str(e)}\"'
                            )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2130, procedure terminated'
    )
    return True


"""
In this function:
- Create drilldown searches collection for flx
- Create default metric collection for flx
"""


def trackme_schema_upgrade_2131(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2131, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Create Kvstore collections and transforms for drilldown searches management in splk-flx
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            #
            # Drilldown search collection
            #

            # set
            transform_name = f"trackme_{component}_drilldown_searches_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_drilldown_searches_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_drilldown_searches"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", successfully created the collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", successfully created the transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the transform, transform="{transform_name}", exception="{str(e)}"'
                )

            #
            # Default metric collection
            #

            # set
            transform_name = f"trackme_{component}_default_metric_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_default_metric_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_default_metric"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the collection, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", successfully created the collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )

                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", successfully created the transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2131, tenant_id="{tenant_id}", failed to create the transform, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2131, procedure terminated'
    )
    return True


"""
In this function:
- Update Workload trackers (splk-wlk) to use the source splunk-svc-search-attribution instead of splunk-svc-consumer
- Update Flex trackers configured for SVC tracking to use the source splunk-svc-search-attribution instead of splunk-svc-consumer
"""


def trackme_schema_upgrade_2132(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2132, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # splk-wlk: Update Workload SVC trackers to switch to the new index
        #

        if (
            vtenant_record.get("tenant_wlk_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", component="wlk", processing with Workload tracker updates'
            )

            #
            # Trackers updates
            #

            # retrieve the list of scheduler reports to be processed
            collection_trackers_name = (
                f"kv_trackme_wlk_hybrid_trackers_tenant_{tenant_id}"
            )
            collection_trackers = service.kvstore[collection_trackers_name]

            trackers_dict = {}
            trackers_to_process = []
            trackers_to_process_kos = []

            # get records from the KVstore
            trackers_records = collection_trackers.data.query()

            for tracker_record in trackers_records:
                tracker_name = tracker_record.get("tracker_name")
                tracker_kos = tracker_record.get("knowledge_objects")

                # if the tracker_name starts by scheduler_
                if re.search("^splunkcloud_", tracker_name):
                    trackers_to_process.append(tracker_name)
                    trackers_to_process_kos.append(tracker_kos)

                    trackers_dict[tracker_name] = {
                        "knowledge_objects": json.loads(tracker_kos),
                    }

            # loop through the trackers (wrapper)
            for tracker_shortname in trackers_to_process:
                tracker_name = (
                    f"trackme_wlk_hybrid_{tracker_shortname}_wrapper_tenant_{tenant_id}"
                )

                tracker_kos = trackers_dict[tracker_shortname]["knowledge_objects"]

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", failed to retrieve the current search definition, tracker_name="{tracker_name}", exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_account = tracker_kos["properties"][0]["account"]
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", tracker_name="{tracker_name}", account={tracker_account}, tracker_current_search="{tracker_current_search}", tracker_kos="{json.dumps(tracker_kos, indent=2)}"'
                )

                # in tracker_current_search, replace:
                #  splunk-svc-consumer
                # with:
                #  splunk-svc-search-attribution

                tracker_new_search = re.sub(
                    r"splunk-svc-consumer",
                    r"splunk-svc-search-attribution",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # splk-flx: Update Flex Object trackers that would track SVC usage
        #

        if (
            vtenant_record.get("tenant_flx_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", component="flx", processing with Flex Objects tracker updates'
            )

            component = "flx"

            # A list to store trackers to be processed
            trackers_to_process = []

            try:
                tracker_kos = json.loads(
                    vtenant_record.get(f"tenant_{component}_hybrid_objects")
                )
                tracker_reports = tracker_kos.get("reports")
            except Exception as e:
                tracker_reports = []

            for tracker_report in tracker_reports:
                if "_wrapper_" in tracker_report:
                    trackers_to_process.append(tracker_report)

            # loop through abstract reports
            for tracker_name in trackers_to_process:

                # get the current search definition
                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", failed to retrieve the current search definition, tracker_name="{tracker_name}", exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search")
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                # get the search definition, if it contains splunk-svc-consumer, process, otherwise skip
                if re.search(
                    "splunk-svc-consumer", tracker_current_search
                ):
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, processing Flex tracker, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, skipping Flex tracker, tenant_id="{tenant_id}", tracker_name="{tracker_name}", tracker_current_search="{tracker_current_search}"'
                    )
                    continue

                # in tracker_current_search, replace the sentence:
                #  splunk-svc-consumer
                # with:
                #  splunk-svc-search-attribution

                tracker_new_search = re.sub(
                    r"splunk-svc-consumer",
                    r"splunk-svc-search-attribution",
                    tracker_current_search,
                )

                # update the search definition
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                    "schedule_window": "5",
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", component="splk-{component}", update report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", component="splk-{component}", successfully updated report definition, report="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2132, tenant_id="{tenant_id}", component="splk-{component}", failed to update the report definition, report="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2132, procedure terminated'
    )
    return True



"""
In this function:
- Update all components main transforms definition
- Migrate time policies from old fields and format to the new time policies unified format
- Create the notes common collection and transform
"""


def trackme_schema_upgrade_2300(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2300, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Vtenant account preferences
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

        #
        # Update the Splunk Remote account preferences
        #

        update_remote_account_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            remote_account_default,
        )

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update main transforms
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            #
            # Migrate existing records: derive monitoring_time_policy from old fields
            #

            try:
                # Determine the field names for monitoring days and hours based on component
                if component in ("dsm", "dhm"):
                    wdays_field = "data_monitoring_wdays"
                    hours_field = "data_monitoring_hours_ranges"
                elif component in ("flx", "wlk", "fqm"):
                    wdays_field = "monitoring_wdays"
                    hours_field = "monitoring_hours_ranges"
                else:
                    # mhm doesn't have these fields, skip
                    wdays_field = None
                    hours_field = None

                # Get all existing records from the collection
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", starting migration of monitoring_time_policy, collection="{collection_name}"'
                )

                collection = service.kvstore[collection_name]
                existing_records, existing_keys, existing_dict = get_kv_collection(
                    collection, collection_name
                )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", found {len(existing_records)} existing records to migrate'
                )

                def is_default_value(value, field_type):
                    """
                    Check if a value is the default value for the field.
                    
                    Args:
                        value: The field value (can be None, empty string, or a string)
                        field_type: "wdays" or "hours"
                    
                    Returns:
                        True if the value is default, False otherwise
                    """
                    try:
                        if value is None or value == "":
                            return True
                        
                        value_str = str(value).strip().lower()
                        
                        if field_type == "wdays":
                            # Default is "auto:all_days"
                            return value_str == "" or value_str == "auto:all_days"
                        elif field_type == "hours":
                            # Default is "auto:all_ranges"
                            return value_str == "" or value_str == "auto:all_ranges"
                        
                        return False
                    except Exception:
                        # If anything goes wrong, assume it's not default to be safe
                        return False

                def derive_monitoring_time_policy_and_rules(record, wdays_field, hours_field):
                    """
                    Derive monitoring_time_policy and monitoring_time_rules from old fields.
                    
                    Old format:
                    - wdays: "auto:all_days", "manual:all_days", "auto:monday-to-friday", 
                             "manual:monday-to-friday", "auto:monday-to-saturday", 
                             "manual:monday-to-saturday", or "manual:1,2,3,4,5" (custom days)
                    - hours: "auto:all_ranges", "manual:all_ranges", "auto:08h-to-20h", 
                             "manual:08h-to-20h", or "manual:8,9,10,11,12,13,14,15" (custom hours)
                    
                    Returns tuple: (monitoring_time_policy, monitoring_time_rules, should_migrate)
                    - monitoring_time_policy: predefined policy string or None if custom rules needed
                    - monitoring_time_rules: JSON string of dictionary or None
                    - should_migrate: True if migration should proceed, False if both fields are defaults
                    
                    Raises:
                        Exception: Re-raises any exception that occurs during processing
                    """
                    try:
                        # Get the old field values
                        wdays_value = record.get(wdays_field) if wdays_field else None
                        hours_value = record.get(hours_field) if hours_field else None

                        # Check if both are defaults - if so, skip migration
                        wdays_is_default = is_default_value(wdays_value, "wdays")
                        hours_is_default = is_default_value(hours_value, "hours")
                        
                        if wdays_is_default and hours_is_default:
                            # Both are defaults, skip migration
                            return (None, None, False)

                        # Normalize values - convert to string and strip whitespace
                        if wdays_value is not None:
                            wdays_str = str(wdays_value).strip()
                        else:
                            wdays_str = ""
                        
                        if hours_value is not None:
                            hours_str = str(hours_value).strip()
                        else:
                            hours_str = ""

                        # If a field is default, use the default value for processing
                        if not wdays_str or wdays_is_default:
                            wdays_str = "auto:all_days"
                        if not hours_str or hours_is_default:
                            hours_str = "auto:all_ranges"

                        wdays_lower = wdays_str.lower()
                        hours_lower = hours_str.lower()

                        # Parse wdays pattern
                        wdays_pattern = None
                        custom_wdays = None
                        
                        if "all_days" in wdays_lower:
                            wdays_pattern = "all_days"
                        elif "monday-to-friday" in wdays_lower:
                            wdays_pattern = "monday-to-friday"
                            custom_wdays = [1, 2, 3, 4, 5]  # Monday-Friday
                        elif "monday-to-saturday" in wdays_lower:
                            wdays_pattern = "monday-to-saturday"
                            custom_wdays = [1, 2, 3, 4, 5, 6]  # Monday-Saturday
                        elif wdays_str.startswith("manual:") and "," in wdays_str:
                            # Custom days: "manual:1,2,3,4,5"
                            try:
                                days_part = wdays_str.replace("manual:", "").strip()
                                custom_wdays = [int(d.strip()) for d in days_part.split(",") if d.strip()]
                                wdays_pattern = "custom"
                            except Exception as e:
                                get_effective_logger().warning(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to parse custom wdays: "{wdays_str}", exception="{str(e)}"'
                                )
                                wdays_pattern = "all_days"  # Fallback
                        else:
                            # Unknown format, default to all_days
                            wdays_pattern = "all_days"

                        # Parse hours pattern
                        hours_pattern = None
                        custom_hours = None
                        
                        if "all_ranges" in hours_lower:
                            hours_pattern = "all_ranges"
                        elif "08h-to-20h" in hours_lower or "08-to-20" in hours_lower:
                            hours_pattern = "08h-to-20h"
                            custom_hours = list(range(8, 20))  # 8am to 7:59pm (hours 8-19)
                        elif hours_str.startswith("manual:") and "," in hours_str:
                            # Custom hours: "manual:8,9,10,11,12,13,14,15"
                            try:
                                hours_part = hours_str.replace("manual:", "").strip()
                                custom_hours = [int(h.strip()) for h in hours_part.split(",") if h.strip()]
                                hours_pattern = "custom"
                            except Exception as e:
                                get_effective_logger().warning(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to parse custom hours: "{hours_str}", exception="{str(e)}"'
                                )
                                hours_pattern = "all_ranges"  # Fallback
                        else:
                            # Unknown format, default to all_ranges
                            hours_pattern = "all_ranges"

                        # Convert to new format
                        # Case 1: All days + All hours = all_time
                        if wdays_pattern == "all_days" and hours_pattern == "all_ranges":
                            return ("all_time", None, True)
                        
                        # Case 2: Monday-to-Friday + All hours = business_days_all_hours
                        elif wdays_pattern == "monday-to-friday" and hours_pattern == "all_ranges":
                            return ("business_days_all_hours", None, True)
                        
                        # Case 3: Monday-to-Friday + 08h-to-20h = business_days_08h_20h
                        elif wdays_pattern == "monday-to-friday" and hours_pattern == "08h-to-20h":
                            return ("business_days_08h_20h", None, True)
                        
                        # Case 4: Monday-to-Saturday + All hours = monday_saturday_all_hours
                        elif wdays_pattern == "monday-to-saturday" and hours_pattern == "all_ranges":
                            return ("monday_saturday_all_hours", None, True)
                        
                        # Case 5: Monday-to-Saturday + 08h-to-20h = monday_saturday_08h_20h
                        elif wdays_pattern == "monday-to-saturday" and hours_pattern == "08h-to-20h":
                            return ("monday_saturday_08h_20h", None, True)
                        
                        # Case 6: Custom patterns - need to create monitoring_time_rules
                        else:
                            # Build monitoring_time_rules dictionary
                            rules_dict = {}
                            
                            # Determine which days to apply
                            if custom_wdays:
                                days_to_apply = custom_wdays
                            elif wdays_pattern == "all_days":
                                days_to_apply = [0, 1, 2, 3, 4, 5, 6]  # All days
                            elif wdays_pattern == "monday-to-friday":
                                days_to_apply = [1, 2, 3, 4, 5]
                            elif wdays_pattern == "monday-to-saturday":
                                days_to_apply = [1, 2, 3, 4, 5, 6]
                            else:
                                days_to_apply = [0, 1, 2, 3, 4, 5, 6]  # Fallback to all days
                            
                            # Determine which hours to apply
                            if custom_hours:
                                hours_to_apply = custom_hours
                            elif hours_pattern == "all_ranges":
                                hours_to_apply = list(range(24))  # All hours 0-23
                            elif hours_pattern == "08h-to-20h":
                                hours_to_apply = list(range(8, 20))  # 8am to 7:59pm
                            else:
                                hours_to_apply = list(range(24))  # Fallback to all hours
                            
                            # Create rules dictionary: {day: [hours]}
                            for day in days_to_apply:
                                rules_dict[str(day)] = hours_to_apply
                            
                            # Return with policy set to None (will use rules instead)
                            return (None, json.dumps(rules_dict), True)
                    except Exception as e:
                        # If anything goes wrong during derivation, log and re-raise
                        # This will be caught by the caller's try-except
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", error in derive_monitoring_time_policy_and_rules, exception="{str(e)}"'
                        )
                        raise

                # Process records
                records_to_update = []
                records_updated_count = 0
                records_skipped_count = 0
                records_error_count = 0

                for record in existing_records:
                    try:
                        record_key = record.get("_key")
                        record_updated = False

                        # Check if monitoring_time_policy is missing or empty
                        current_policy = record.get("monitoring_time_policy")
                        current_rules = record.get("monitoring_time_rules")
                        
                        if (not current_policy or current_policy == "") and (not current_rules or current_rules == ""):
                            # Only migrate if we have the old fields for this component
                            if wdays_field and hours_field:
                                try:
                                    # Derive the policy and rules from old fields
                                    new_policy, new_rules, should_migrate = derive_monitoring_time_policy_and_rules(
                                        record, wdays_field, hours_field
                                    )
                                    
                                    # Skip if both fields are defaults
                                    if not should_migrate:
                                        records_skipped_count += 1
                                        get_effective_logger().debug(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", record_key="{record_key}", skipping migration (both fields are defaults)'
                                        )
                                        continue
                                    
                                    if new_policy:
                                        record["monitoring_time_policy"] = new_policy
                                        record_updated = True
                                        get_effective_logger().debug(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", record_key="{record_key}", set monitoring_time_policy="{new_policy}" from old fields'
                                        )
                                    
                                    if new_rules:
                                        record["monitoring_time_rules"] = new_rules
                                        record_updated = True
                                        get_effective_logger().debug(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", record_key="{record_key}", set monitoring_time_rules="{new_rules}" from old fields'
                                        )
                                except Exception as e_record_processing:
                                    # Log error for this specific record but continue with next record
                                    record_key_value = record.get("_key", "unknown")
                                    records_error_count += 1
                                    get_effective_logger().error(
                                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to process record for migration, record_key="{record_key_value}", exception="{str(e_record_processing)}"'
                                    )
                                    # Skip this record and continue with next
                                    continue

                        if record_updated:
                            # Update mtime to reflect the migration
                            record["mtime"] = time.time()
                            records_to_update.append(record)
                            records_updated_count += 1
                        else:
                            records_skipped_count += 1
                    except Exception as e_record:
                        # Catch any unexpected errors during record processing
                        record_key_value = record.get("_key", "unknown") if record else "unknown"
                        records_error_count += 1
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", unexpected error processing record, record_key="{record_key_value}", exception="{str(e_record)}"'
                        )
                        # Continue with next record
                        continue

                # Batch update records
                if records_to_update:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", updating {len(records_to_update)} records with monitoring_time_policy'
                    )

                    # Process in chunks of 500 for batch updates
                    chunk_size = 500
                    for i in range(0, len(records_to_update), chunk_size):
                        chunk = records_to_update[i : i + chunk_size]
                        try:
                            collection.data.batch_save(*chunk)
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", successfully updated batch {i // chunk_size + 1}, records_count={len(chunk)}'
                            )
                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to update batch {i // chunk_size + 1}, exception="{str(e)}"'
                            )
                            # Fallback to individual updates if batch fails
                            for record in chunk:
                                try:
                                    collection.data.update(
                                        record.get("_key"), json.dumps(record)
                                    )
                                except Exception as e2:
                                    record_key_value = record.get("_key")
                                    get_effective_logger().error(
                                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to update individual record, record_key="{record_key_value}", exception="{str(e2)}"'
                                    )

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", migration completed, records_updated={records_updated_count}, records_skipped={records_skipped_count}, records_error={records_error_count}'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", no records needed migration for monitoring_time_policy'
                    )

            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", component="{component}", failed to migrate monitoring_time_policy, collection="{collection_name}", exception="{str(e)}"'
                )
                # Continue with other components even if one fails

        #
        # Create the notes common collection and transform
        #

        # set
        transform_name = f"trackme_notes_tenant_{tenant_id}"
        collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        transform_fields = collections_dict[f"trackme_notes"]
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", successfully KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        #
        # END
        #

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2300, tenant_id="{tenant_id}", schema migration 2300, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2304(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2304, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Update stateful alerts to use new trackmestateful custom command
        #

        # get alert object from field tenant_alert_objects
        alert_objects = vtenant_record.get("tenant_alert_objects", None)

        # check if we have alert objects
        if alert_objects:

            # load the alert objects as a json object
            try:
                alert_objects = json.loads(alert_objects)
            except Exception as e:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", no alerts found for update.'
                )
                alert_objects = None

            # Ensure alert_objects is a dictionary before accessing .get()
            if alert_objects and isinstance(alert_objects, dict):
                # get list of alerts
                alerts_list = alert_objects.get("alerts", [])

                # for each alert
                for alert_name in alerts_list:

                    alert_current = None
                    try:
                        alert_current = service.saved_searches[alert_name]
                    except Exception as e:
                        pass

                    if alert_current:
                        # Check if this alert has trackme_stateful_alert action
                        actions = alert_current.content.get("actions", "")
                        if isinstance(actions, str):
                            actions_list = [a.strip() for a in actions.split(",") if a.strip()]
                        elif isinstance(actions, list):
                            actions_list = actions
                        else:
                            actions_list = []

                        # Only process stateful alerts
                        if "trackme_stateful_alert" in actions_list:
                            alert_current_search = alert_current.content.get("search")
                            alert_current_earliest_time = alert_current.content.get(
                                "dispatch.earliest_time"
                            )
                            alert_current_latest_time = alert_current.content.get(
                                "dispatch.latest_time"
                            )

                            # Set earliest_time to -10m for stateful alerts (new default)
                            new_earliest_time = "-10m"
                            needs_update = False
                            update_reason = []

                            # Check if search needs to be updated to use trackmestateful command
                            # Handle case where search attribute might be None or empty
                            if not alert_current_search or "trackmestateful" not in alert_current_search:
                                # Build new search query using trackmestateful custom command
                                # Pattern: | trackmestateful tenant_id="${tenantId}" | `trackme_apply_maintenance_mode_v2` | sort limit=0 _time
                                new_alert_search = f'| trackmestateful tenant_id="{tenant_id}"\n| `trackme_apply_maintenance_mode_v2`\n| sort limit=0 _time'
                                needs_update = True
                                update_reason.append("search query")
                            else:
                                new_alert_search = alert_current_search

                            # Check if earliest_time needs to be updated
                            if alert_current_earliest_time != new_earliest_time:
                                needs_update = True
                                update_reason.append("earliest_time")

                            # Only update if something needs to be changed
                            if needs_update:
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", updating stateful alert ({", ".join(update_reason)}), current_earliest_time="{alert_current_earliest_time}", new_earliest_time="{new_earliest_time}"'
                                )

                                # update the alert definition
                                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                                data = {
                                    "tenant_id": tenant_id,
                                    "report_name": alert_name,
                                    "report_search": new_alert_search,
                                    "earliest_time": new_earliest_time,
                                    "latest_time": alert_current_latest_time,
                                }

                                try:
                                    response = requests.post(
                                        url,
                                        headers={
                                            "Authorization": f'Splunk {reqinfo["session_key"]}'
                                        },
                                        data=json.dumps(data),
                                        verify=False,
                                        timeout=600,
                                    )
                                    if response.status_code not in (200, 201, 202, 204):
                                        get_effective_logger().error(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2304, tenant_id="{tenant_id}", update alert definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                                        )
                                    else:
                                        get_effective_logger().info(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2304, tenant_id="{tenant_id}", successfully updated stateful alert definition, alert="{alert_name}"'
                                        )
                                except Exception as e:
                                    get_effective_logger().error(
                                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2304, tenant_id="{tenant_id}", failed to update the alert definition, report="{alert_name}", exception="{str(e)}"'
                                    )
                            else:
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", alert_name="{alert_name}", stateful alert already up to date, earliest_time="{alert_current_earliest_time}", skipping update.'
                                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2304, procedure terminated'
    )
    return True


"""
In this function:
- Refresh central lookup definitions for all components
- Refresh lookup definitions for FQM and FLX threshold KVStore collections
- Remove and re-create the lookup definition for trackme_fqm_thresholds if FQM is enabled
- Remove and re-create the lookup definition for trackme_flx_thresholds if FLX is enabled
"""


def trackme_schema_upgrade_2305(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2305, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update main transforms
        #

        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Refresh lookup definitions for threshold collections
        #

        # Determine which components to process based on tenant enablement
        components_to_process = []

        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            #
            # Refresh threshold lookup definition
            #

            # set
            transform_name = f"trackme_{component}_thresholds_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_thresholds_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_thresholds"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2305, tenant_id="{tenant_id}", component="{component}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2305, procedure terminated'
    )
    return True


"""
In this function:
- Refresh central lookup definitions for: flx
"""


def trackme_schema_upgrade_2306(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2306, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Get permissions and sharing levels
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        #
        # Update main transforms
        #

        components_to_process = []

        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2306, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2306, procedure terminated'
    )
    return True


"""
In this function:
- Refresh central lookup definitions for all components (DSM, DHM, MHM, FLX, FQM, WLK)
- Refresh lookup definitions for FQM and FLX threshold KVStore collections
- Migrate existing tenant alerts to replace index subsearch macros with explicit index constraints
- Replace `trackme_idx(tenant_id)`, `trackme_metrics_idx(tenant_id)`, `trackme_notable_idx(tenant_id)`,
  and `trackme_audit_idx(tenant_id)` macro calls with resolved index=<name> constraints
- This eliminates unnecessary subsearch overhead (each macro consumed a Splunk search slot)
- Uses precise regex matching to avoid incorrect replacements
- Only updates alerts that actually contain macro references
- Never fails the migration: all operations are wrapped in try/except
"""


def trackme_schema_upgrade_2308(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2308, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Refresh central lookup definitions for all components
        #

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # Determine which components to process based on tenant enablement
        components_to_process = []

        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")

        for component in components_to_process:

            #
            # update main collection transforms
            #

            # set
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Refresh lookup definitions for threshold collections (FQM and FLX)
        #

        threshold_components = []

        if vtenant_record.get("tenant_fqm_enabled") == 1:
            threshold_components.append("fqm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            threshold_components.append("flx")

        for component in threshold_components:

            #
            # Refresh threshold lookup definition
            #

            # set
            transform_name = f"trackme_{component}_thresholds_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_thresholds_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_thresholds"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", failed to delete the threshold transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", successfully deleted threshold transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", failed to delete the threshold transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", create threshold transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", successfully created threshold transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", component="{component}", failed to create the threshold transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Resolve tenant-specific index names once for all alerts
        #

        try:
            tenant_indexes = trackme_idx_for_tenant(
                reqinfo["session_key"], reqinfo["server_rest_uri"], tenant_id
            )
            tenant_trackme_summary_idx = tenant_indexes.get("trackme_summary_idx", "trackme_summary")
            tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")
            tenant_trackme_notable_idx = tenant_indexes.get("trackme_notable_idx", "trackme_notable")
            tenant_trackme_audit_idx = tenant_indexes.get("trackme_audit_idx", "trackme_audit")

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'resolved tenant indexes: summary="{tenant_trackme_summary_idx}", '
                f'metric="{tenant_trackme_metric_idx}", notable="{tenant_trackme_notable_idx}", '
                f'audit="{tenant_trackme_audit_idx}"'
            )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'failed to resolve tenant indexes, skipping alert migration, exception="{str(e)}"'
            )
            # Cannot proceed without resolved indexes — return True to not block the upgrade
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2308, procedure terminated (skipped due to index resolution failure)'
            )
            return True

        #
        # Build precise regex patterns for macro replacement
        # Each pattern matches the backtick-enclosed macro call with the tenant_id argument
        # The macro argument can be quoted or unquoted, and may contain various tenant_id formats
        #
        # Pattern explanation:
        #   `trackme_idx(...)` where ... is any non-empty content that does not contain backticks
        #   This is intentionally strict to avoid matching unexpected content
        #

        macro_replacements = [
            {
                "macro_name": "trackme_idx",
                "pattern": re.compile(r'`trackme_idx\([^)`]+\)`'),
                "replacement": f'index="{tenant_trackme_summary_idx}"',
            },
            {
                "macro_name": "trackme_metrics_idx",
                "pattern": re.compile(r'`trackme_metrics_idx\([^)`]+\)`'),
                "replacement": f'index="{tenant_trackme_metric_idx}"',
            },
            {
                "macro_name": "trackme_notable_idx",
                "pattern": re.compile(r'`trackme_notable_idx\([^)`]+\)`'),
                "replacement": f'index="{tenant_trackme_notable_idx}"',
            },
            {
                "macro_name": "trackme_audit_idx",
                "pattern": re.compile(r'`trackme_audit_idx\([^)`]+\)`'),
                "replacement": f'index="{tenant_trackme_audit_idx}"',
            },
        ]

        #
        # Update alerts: replace index subsearch macros with explicit index constraints
        #

        # get alert object from field tenant_alert_objects
        alert_objects = vtenant_record.get("tenant_alert_objects", None)

        # check if we have alert objects
        if alert_objects:

            # load the alert objects as a json object
            try:
                alert_objects = json.loads(alert_objects)
            except Exception as e:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", no alerts found for update.'
                )
                alert_objects = None

            # Ensure alert_objects is a dictionary before accessing .get()
            if alert_objects and isinstance(alert_objects, dict):
                # get list of alerts
                alerts_list = alert_objects.get("alerts", [])

                # for each alert
                for alert_name in alerts_list:

                    try:
                        alert_current = None
                        try:
                            alert_current = service.saved_searches[alert_name]
                        except Exception as e:
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                                f'alert_name="{alert_name}", saved search not found, skipping.'
                            )

                        if alert_current:
                            alert_current_search = alert_current.content.get("search")
                            alert_current_earliest_time = alert_current.content.get(
                                "dispatch.earliest_time"
                            )
                            alert_current_latest_time = alert_current.content.get(
                                "dispatch.latest_time"
                            )

                            # Skip if search is empty or None
                            if not alert_current_search:
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                                    f'alert_name="{alert_name}", alert search is empty, skipping.'
                                )
                                continue

                            # Apply each macro replacement pattern
                            alert_new_search = alert_current_search
                            replaced_macros = []

                            for macro_def in macro_replacements:
                                if macro_def["pattern"].search(alert_new_search):
                                    alert_new_search = macro_def["pattern"].sub(
                                        macro_def["replacement"], alert_new_search
                                    )
                                    replaced_macros.append(macro_def["macro_name"])

                            # Only update if at least one macro was replaced
                            if replaced_macros:

                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                                    f'alert_name="{alert_name}", replacing macros: {", ".join(replaced_macros)}, '
                                    f'original_search="{alert_current_search}"'
                                )

                                # update the alert definition
                                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                                data = {
                                    "tenant_id": tenant_id,
                                    "report_name": alert_name,
                                    "report_search": alert_new_search,
                                    "earliest_time": alert_current_earliest_time,
                                    "latest_time": alert_current_latest_time,
                                }

                                try:
                                    response = requests.post(
                                        url,
                                        headers={
                                            "Authorization": f'Splunk {reqinfo["session_key"]}'
                                        },
                                        data=json.dumps(data),
                                        verify=False,
                                        timeout=600,
                                    )
                                    if response.status_code not in (200, 201, 202, 204):
                                        get_effective_logger().error(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", '
                                            f'update alert definition has failed, alert="{alert_name}", '
                                            f'response.status_code="{response.status_code}", response.text="{response.text}"'
                                        )
                                    else:
                                        get_effective_logger().info(
                                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", '
                                            f'successfully updated alert definition, alert="{alert_name}", replaced_macros="{", ".join(replaced_macros)}"'
                                        )
                                except Exception as e:
                                    get_effective_logger().error(
                                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", '
                                        f'failed to update the alert definition, alert="{alert_name}", exception="{str(e)}"'
                                    )
                            else:
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                                    f'alert_name="{alert_name}", no index macros found in search, skipping.'
                                )

                    except Exception as e:
                        # Catch-all: never let a single alert failure block the migration
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2308, tenant_id="{tenant_id}", '
                            f'unexpected error processing alert="{alert_name}", exception="{str(e)}"'
                        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2308, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2312(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2312:
    - Create variable delay KVstore collections for DSM and DHM components
    - Create corresponding transforms for the variable delay collections
    - Update main DSM/DHM transforms to include the new variable_delay_policy, variable_delay_active_slot, variable_delay_active_threshold fields
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2312, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # ko_acl for collections and transforms
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        #
        # Part 1: Create variable delay collections and transforms for DSM and DHM
        #

        variable_delay_components = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            variable_delay_components.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            variable_delay_components.append("dhm")

        for component in variable_delay_components:

            collection_name = f"kv_trackme_{component}_variable_delay_tenant_{tenant_id}"
            transform_name = f"trackme_{component}_variable_delay_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_variable_delay"]

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", successfully created KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform if collection was created
            if kvstore_created:

                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", successfully created transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # Part 2: Update main DSM/DHM collection transforms to include new variable_delay fields
        #

        # Determine all components to refresh transforms for
        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")

        for component in components_to_process:

            # update main collection transform
            transform_name = f"trackme_{component}_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Part 3: Create variable delay review tracker reports for DSM and DHM
        #

        for component in variable_delay_components:

            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": trackme_default_sharing,
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }

            report_name = (
                f"trackme_{component}_variable_delay_review_tracker_tenant_{tenant_id}"
            )
            report_search = f'| trackmesplkvariabledelayreview tenant_id="{tenant_id}" component="{component}" review_frequency_sec=604800 deviation_threshold_pct=20 lookback="-30d" method="perc95" min_samples=10 max_threshold_sec=604800 max_runtime=7200'
            report_properties = {
                "description": "This scheduled report manages variable delay auto-review for TrackMe",
                "is_scheduled": True,
                "cron_schedule": "30 3 * * *" if component == "dhm" else "30 2 * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", create variable delay review tracker report has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", successfully created variable delay review tracker report, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2312, tenant_id="{tenant_id}", component="{component}", failed to create variable delay review tracker report, report="{report_name}", exception="{str(e)}"'
                )

        #
        # Part 4: Set default delay policy to static for migrated tenants (pre-2.3.12)
        # Ensures existing behavior is preserved: static threshold, no variable delay defaults
        #
        updated_vtenant_data = {
            "dsm_default_delay_policy": "static",
            "dsm_default_delay_threshold_sec": 3600,
            "dsm_variable_delay_default_slots": "{}",
            "dsm_variable_delay_default": "3600",
            "dhm_default_delay_policy": "static",
            "dhm_default_delay_threshold_sec": 86400,
            "dhm_variable_delay_default_slots": "{}",
            "dhm_variable_delay_default": "86400",
        }
        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
            updated_vtenant_data,
        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2312, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2313(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2313:
    - Update FLX threshold collection transforms to include new variable threshold fields
      (variable_threshold_enabled, variable_threshold_default, variable_threshold_slots)
    - Create per-component lagging class KVstore collections and transforms (trackme_dsm_lagging_classes,
      trackme_dhm_lagging_classes) with new fields: match_mode, delay_mode, variable_delay_default,
      variable_delay_slots, ctime, mtime
    - Migrate existing records from the old common lagging classes collection
      (kv_trackme_common_lagging_classes) to the new component-specific collections,
      with duplicate detection to ensure idempotent re-runs
    - Update DSM/DHM/FLX/FQM/WLK outliers entity rules collection transforms to include
      splk_outliers_min_days_history field for confidence config mismatch detection
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2313, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # ko_acl for collections and transforms
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        #
        # Update FLX threshold collection transforms to include variable threshold fields
        #

        components_to_process = []
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")

        for component in components_to_process:

            # update threshold collection transform
            transform_name = f"trackme_{component}_thresholds_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_thresholds_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_thresholds"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully deleted transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to delete the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create component-specific lagging class collections and migrate data from common collection
        #

        components_lc = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_lc.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_lc.append("dhm")

        for component in components_lc:

            collection_name = f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
            transform_name = f"trackme_{component}_lagging_classes_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_lagging_classes"]

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create KVstore collection has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully created KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create KVstore collection has failed, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform (only if collection was created successfully)
            if kvstore_created:
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create transform has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully created transform, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create transform has failed, transform="{transform_name}", exception="{str(e)}"'
                    )

        # Migrate data from old common lagging classes collection to component-specific collections
        if len(components_lc) > 0:
            old_collection_name = f"kv_trackme_common_lagging_classes_tenant_{tenant_id}"
            try:
                old_collection = service.kvstore[old_collection_name]
                old_records = old_collection.data.query()
            except Exception as e:
                old_records = []
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", could not read old common lagging classes collection, exception="{str(e)}"'
                )

            if old_records:
                now = time.time()

                for old_record in old_records:
                    old_object = old_record.get("object", "all")
                    old_name = old_record.get("name", "")
                    old_level = old_record.get("level", "")
                    old_value_lag = old_record.get("value_lag", "")
                    old_value_delay = old_record.get("value_delay", "")
                    old_comment = old_record.get("comment", "")
                    old_mtime = old_record.get("mtime", now)

                    # Determine target components
                    target_components = []
                    if old_object == "splk-dsm" and "dsm" in components_lc:
                        target_components.append("dsm")
                    elif old_object == "splk-dhm" and "dhm" in components_lc:
                        target_components.append("dhm")
                    elif old_object == "all":
                        target_components = [c for c in components_lc]

                    new_record = {
                        "name": old_name,
                        "level": old_level,
                        "match_mode": "exact",
                        "value_delay": str(old_value_delay),
                        "delay_mode": "static",
                        "variable_delay_default": "",
                        "variable_delay_slots": "",
                        "value_lag": str(old_value_lag),
                        "comment": old_comment,
                        "ctime": old_mtime,
                        "mtime": old_mtime,
                    }

                    for target_component in target_components:
                        target_collection_name = f"kv_trackme_{target_component}_lagging_classes_tenant_{tenant_id}"
                        try:
                            target_collection = service.kvstore[target_collection_name]
                            # Check for existing record to prevent duplicates on re-run
                            existing = target_collection.data.query(
                                query=json.dumps({"name": old_name, "level": old_level})
                            )
                            if existing:
                                get_effective_logger().info(
                                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", skipping duplicate lagging class record, name="{old_name}", level="{old_level}", target_component="{target_component}"'
                                )
                                continue
                            target_collection.data.insert(json.dumps(new_record))
                            get_effective_logger().info(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", migrated lagging class record, name="{old_name}", level="{old_level}", from common to {target_component}'
                            )
                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", failed to migrate lagging class record, name="{old_name}", target_component="{target_component}", exception="{str(e)}"'
                            )

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", lagging classes data migration completed, migrated {len(old_records)} records'
                )

        #
        # Update outliers entity rules collection transforms to include splk_outliers_min_days_history field
        #

        outliers_components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            outliers_components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            outliers_components_to_process.append("dhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            outliers_components_to_process.append("flx")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            outliers_components_to_process.append("fqm")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            outliers_components_to_process.append("wlk")

        for component in outliers_components_to_process:

            # update outliers entity rules collection transform
            transform_name = f"trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_outliers_entity_rules"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to delete the outliers entity rules transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully deleted outliers entity rules transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to delete the outliers entity rules transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", create outliers entity rules transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", successfully created outliers entity rules transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2313, tenant_id="{tenant_id}", component="{component}", failed to create the outliers entity rules transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2313, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2314(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2314:
    - Update priority policies collection transforms for all components (dsm, dhm, mhm, flx, wlk, fqm)
      to include new lookup-based policy fields: priority_policy_type, priority_policy_lookup_name,
      priority_policy_lookup_field_mappings, priority_policy_lookup_priority_field,
      priority_policy_lookup_priority_mappings, priority_policy_lookup_match_mode
    - Update SLA sub-collection transforms to fix sla_reason -> sla_class_reason field name
    - Update SLA policies collection transforms to include lookup-based policy fields
    - Update Tags sub-collection transforms to include tags_auto_policies field
    - Existing regex-based policies remain fully backward compatible (missing policy_type
      defaults to "regex" in all backend code)
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2314, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # ko_acl for collections and transforms
        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        #
        # Update priority policies collection transforms for all enabled components
        # to include lookup-based policy fields
        #

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            components_to_process.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        for component in components_to_process:

            # update priority policies collection transform
            transform_name = f"trackme_{component}_priority_policies_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_priority_policies_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_priority_policies"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the priority policies transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully deleted priority policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the priority policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform with updated fields
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", create priority policies transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully created priority policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to create the priority policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update SLA sub-collection and SLA policies collection transforms for all enabled components
        # to fix sla_reason -> sla_class_reason field name and include lookup-based policy fields
        #

        for component in components_to_process:

            # SLA sub-collection transform (fix sla_reason -> sla_class_reason)
            transform_name = f"trackme_{component}_sla_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_sla_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_sla"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the SLA sub-collection transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully deleted SLA sub-collection transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the SLA sub-collection transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform with updated fields
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", create SLA sub-collection transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully created SLA sub-collection transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to create the SLA sub-collection transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # SLA policies collection transform (include lookup-based policy fields)
            transform_name = f"trackme_{component}_sla_policies_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_sla_policies_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_sla_policies"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the SLA policies transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully deleted SLA policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the SLA policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform with updated fields
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", create SLA policies transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully created SLA policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to create the SLA policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update Tags sub-collection transforms for all enabled components
        # to include tags_auto_policies field
        #

        for component in components_to_process:

            # Tags sub-collection transform (add tags_auto_policies field)
            transform_name = f"trackme_{component}_tags_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tags_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_tags"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the tags sub-collection transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully deleted tags sub-collection transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the tags sub-collection transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform with updated fields
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", create tags sub-collection transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully created tags sub-collection transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to create the tags sub-collection transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update Tags policies collection transforms for all enabled components
        # to include lookup-based policy fields
        #

        for component in components_to_process:

            # Tags policies collection transform
            transform_name = f"trackme_{component}_tags_policies_tenant_{tenant_id}"
            collection_name = f"kv_trackme_{component}_tags_policies_tenant_{tenant_id}"
            transform_fields = collections_dict[f"trackme_{component}_tags_policies"]

            # delete the transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the tags policies transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully deleted tags policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to delete the tags policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

            # create the transform with updated fields
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", create tags policies transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", successfully created tags policies transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2314, tenant_id="{tenant_id}", component="{component}", failed to create the tags policies transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2314, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2315(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2315:
    - Creates the per-tenant native ML models KVstore collection and transforms
      (kv_trackme_native_ml_models_tenant_<tenant_id>) for storing fitted density
      function models
    - Migrate existing DensityFunction models to TrackMeNativeDensityFunction
      which uses native scipy-based density fitting (trackmefit/trackmeapply commands)
      instead of MLTK's DensityFunction which is broken with pandas 3.0+
    - Sets algorithm to TrackMeNativeDensityFunction, model_storage to kvstore
    - Resets stored search fields to "pending" so next training cycle regenerates
      them with the native commands
    - For non-DensityFunction models, fixes 'by' clause quoting in fit commands
      for compatibility with Splunk AI Toolkit 5.7.0+
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2315, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        #
        # Create the per-tenant native ML models KVstore collection and transforms
        # This collection stores fitted density function models as an alternative to file-based .mlmodel storage
        #

        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(vtenant_record)

        transform_name = f"trackme_native_ml_models_tenant_{tenant_id}"
        collection_name = f"kv_trackme_native_ml_models_tenant_{tenant_id}"
        transform_fields = collections_dict["trackme_native_ml_models"]
        definition_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": "app",
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        # create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "collection_acl": definition_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                    f'create KVstore collection has failed, collection="{collection_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                    f'successfully created KVstore collection, collection="{collection_name}"'
                )
                kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                f'failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
            )

        # create the transforms definition
        if kvstore_created:
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'create transform definition has failed, transform="{transform_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'successfully created transform definition, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                    f'failed to create the transform definition, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Fix DensityFunction 'by' clause quoting in stored ML outlier searches
        # AI Toolkit 5.7.0+ requires field names in the 'by' clause to be quoted
        #

        # Use a regex that specifically targets the 'by' clause within fit commands only,
        # to avoid modifying the 'by' clause in mstats commands (which must remain unquoted)
        # Pattern matches: 'fit <algo> ... by <field>' and quotes the field name
        # Uses non-greedy .+? to match the FIRST 'by' keyword after 'fit', which is the
        # correct one from the fit command syntax (extra parameters come before the by clause)
        # re.DOTALL ensures matching works even if fit and by are on separate lines
        import re
        fit_by_clause_pattern = re.compile(r'(\bfit\b.+?\bby\s+)(?!")(\w+)', re.DOTALL)

        components_to_process = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            components_to_process.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            components_to_process.append("dhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            components_to_process.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            components_to_process.append("wlk")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            components_to_process.append("fqm")

        # search fields that contain DensityFunction fit/apply SPL
        search_fields_to_fix = [
            "ml_model_gen_search",
            "ml_model_render_search",
            "ml_model_simulation_gen_search",
            "ml_model_simulation_render_search",
        ]

        for component in components_to_process:

            collection_outliers_rules_name = (
                f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
            )

            try:
                collection_outliers_rules = service.kvstore[collection_outliers_rules_name]
            except Exception as e:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                    f'collection "{collection_outliers_rules_name}" not found, skipping. exception="{str(e)}"'
                )
                continue

            # get all records with pagination
            collection_records = []
            collection_records_keys = set()

            end = False
            skip_tracker = 0
            while end == False:
                process_collection_records = collection_outliers_rules.data.query(
                    skip=skip_tracker
                )
                if len(process_collection_records) != 0:
                    for item in process_collection_records:
                        if item.get("_key") not in collection_records_keys:
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            records_updated = 0

            # loop through the records
            for outlier_record in collection_records:

                entities_outliers_raw = outlier_record.get("entities_outliers")
                if not entities_outliers_raw:
                    continue

                try:
                    entities_outliers = json.loads(entities_outliers_raw)
                except Exception as e:
                    get_effective_logger().warning(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to parse entities_outliers for record key="{outlier_record.get("_key")}", exception="{str(e)}"'
                    )
                    continue

                record_modified = False
                density_function_migrated = False

                for model_id in entities_outliers:
                    model_data = entities_outliers[model_id]
                    current_algorithm = model_data.get("algorithm", "")

                    # Migrate DensityFunction models to native TrackMe implementation
                    if current_algorithm == "DensityFunction":
                        model_data["algorithm"] = "TrackMeNativeDensityFunction"
                        model_data["model_storage"] = "kvstore"

                        # Reset search fields to "pending" so the next training cycle
                        # regenerates them with the native trackmefit/trackmeapply commands
                        for field_name in search_fields_to_fix:
                            if model_data.get(field_name):
                                model_data[field_name] = "pending"

                        # Reset the model-level last_exec to force ML training to re-run
                        # with the native density function implementation
                        model_data["last_exec"] = 0

                        record_modified = True
                        density_function_migrated = True
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'model_id="{model_id}", migrated algorithm from DensityFunction to TrackMeNativeDensityFunction, reset searches to pending, reset last_exec to 0'
                        )

                    else:
                        # For non-DensityFunction models, still fix by clause quoting if needed
                        for field_name in search_fields_to_fix:
                            search_value = model_data.get(field_name)
                            if search_value and isinstance(search_value, str):
                                new_search_value = fit_by_clause_pattern.sub(
                                    r'\1"\2"', search_value
                                )
                                if new_search_value != search_value:
                                    model_data[field_name] = new_search_value
                                    record_modified = True
                                    get_effective_logger().info(
                                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                                        f'model_id="{model_id}", fixed by clause quoting in field="{field_name}"'
                                    )

                if record_modified:
                    # update the record
                    outlier_record["entities_outliers"] = json.dumps(
                        entities_outliers, indent=2
                    )

                    # Reset last_exec to force ML training to re-run with the native density function
                    if density_function_migrated:
                        outlier_record["last_exec"] = 0

                    # update the KVstore
                    try:
                        collection_outliers_rules.data.update(
                            outlier_record.get("_key"),
                            json.dumps(outlier_record, indent=2),
                        )
                        records_updated += 1
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'failed to update outlier entity rules for record key="{outlier_record.get("_key")}", exception="{str(e)}"'
                        )

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                f'outlier rules by clause fix completed, records_updated={records_updated}, records_total={len(collection_records)}'
            )

        #
        # Update policy collection transforms for all enabled components
        # to include search-based policy fields (search_query, search_earliest, search_latest)
        # Note: MHM is not eligible for ML Outliers above but does have policies
        #

        policy_components = list(components_to_process)
        if vtenant_record.get("tenant_mhm_enabled") == 1 and "mhm" not in policy_components:
            policy_components.append("mhm")

        for component in policy_components:

            policy_collections_to_update = [
                ("priority_policies", f"trackme_{component}_priority_policies"),
                ("sla_policies", f"trackme_{component}_sla_policies"),
                ("tags_policies", f"trackme_{component}_tags_policies"),
            ]

            for policy_label, dict_key in policy_collections_to_update:
                transform_name = f"{dict_key}_tenant_{tenant_id}"
                collection_name = f"kv_{dict_key}_tenant_{tenant_id}"
                transform_fields = collections_dict[dict_key]

                # delete the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'failed to delete the {policy_label} transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'successfully deleted {policy_label} transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to delete the {policy_label} transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # create the transform with updated fields (includes search-based policy fields)
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": definition_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'create {policy_label} transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                            f'successfully created {policy_label} transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to create the {policy_label} transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # Create WLK thresholds KVstore collection and transform for WLK-enabled tenants
        # and seed default threshold records
        #

        if vtenant_record.get("tenant_wlk_enabled") == 1:

            # TrackMe sharing level
            trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
                "trackme_default_sharing"
            ]

            transform_name = f"trackme_wlk_thresholds_tenant_{tenant_id}"
            collection_name = f"kv_trackme_wlk_thresholds_tenant_{tenant_id}"
            transform_fields = collections_dict["trackme_wlk_thresholds"]
            ko_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": trackme_default_sharing,
                "perms.write": tenant_roles_write_perms,
                "perms.read": tenant_roles_read_perms,
            }

            # create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'create WLK thresholds KVstore collection has failed, collection="{collection_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'successfully created WLK thresholds KVstore collection, collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                    f'failed to create the WLK thresholds KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

            # create the transform definition
            if kvstore_created:
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": ko_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                            f'create WLK thresholds transform definition has failed, transform="{transform_name}", response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                            f'successfully created WLK thresholds transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'failed to create the WLK thresholds transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # Seed default WLK threshold records
                try:
                    wlk_thresholds_collection = service.kvstore[collection_name]
                    current_time = time.time()

                    for threshold in wlk_default_thresholds:
                        record = dict(threshold)
                        record["object_id"] = "default"
                        record["mtime"] = current_time
                        try:
                            wlk_thresholds_collection.data.insert(json.dumps(record))
                        except Exception as e:
                            get_effective_logger().error(
                                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                                f'failed to seed WLK default threshold record, metric_name="{record.get("metric_name")}", exception="{str(e)}"'
                            )

                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'successfully seeded {len(wlk_default_thresholds)} default WLK threshold records into collection="{collection_name}"'
                    )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2315, tenant_id="{tenant_id}", '
                        f'failed to seed WLK default threshold records, collection="{collection_name}", exception="{str(e)}"'
                    )

        #
        # Update vtenant account configuration to remove obsolete keys
        # (impact_score_wlk_out_of_monitoring_times is no longer in vtenant_account_default
        # and will be automatically pruned by the maintain_vtenant_account endpoint)
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2315, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2316(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2316:
    - Refreshes central KV collection transforms for all enabled components (DSM, DHM,
      MHM, FLX, FQM, WLK) to ensure field definitions are up-to-date with collections_data.py
    - Adds health tracker task frequency state collection (kv_trackme_health_tracker_state)
      This collection is global (not per-tenant) and is already defined in collections.conf
      and registered in collections_data.py, so this migration only bumps the schema version.
    - Updates policy collection transforms (priority, SLA, tags) for all enabled
      components to include the 'account' field for remote Splunk deployment support
    - Updates delayed entities inspector transforms for DSM/DHM to include progressive
      backoff fields: inspector_consecutive_no_data_count, inspector_last_data_found,
      inspector_backoff_multiplier
    - Creates per-tenant shadow KV collections and transforms for each enabled component
      (kv_trackme_{component}_shadow_tenant_{tenant_id}) for instant UI loading at scale
    - Adds shadow_entity_threshold to vtenant_account configuration
    - Creates per-tenant score cache KV collection (kv_trackme_common_score_cache_tenant_{tenant_id})
      for immediate visibility of false positive and manual score changes
    - Fixes WLK default thresholds regression (PR #685, fixed in PR #801): corrects tenants
      that were seeded with a duplicate skipped_pct_last_24h instead of skipped_pct_last_4h
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2316, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:

        tenant_id = vtenant_record.get("tenant_id")

        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(vtenant_record)

        definition_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": "app",
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        #
        # Refresh central KV collection transforms for all enabled components
        # Safety measure: ensures all component central collection transforms
        # are up-to-date with the latest field definitions from collections_data.py
        #

        central_collections_to_refresh = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            central_collections_to_refresh.append(("dsm", "trackme_dsm"))
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            central_collections_to_refresh.append(("dhm", "trackme_dhm"))
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            central_collections_to_refresh.append(("mhm", "trackme_mhm"))
        if vtenant_record.get("tenant_flx_enabled") == 1:
            central_collections_to_refresh.append(("flx", "trackme_flx"))
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            central_collections_to_refresh.append(("fqm", "trackme_fqm"))
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            central_collections_to_refresh.append(("wlk", "trackme_wlk"))

        for component, dict_key in central_collections_to_refresh:

            transform_name = f"{dict_key}_tenant_{tenant_id}"
            collection_name = f"kv_{dict_key}_tenant_{tenant_id}"
            transform_fields = collections_dict[dict_key]

            # delete the existing transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to delete central collection transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'successfully deleted central collection transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                    f'failed to delete central collection transform, transform="{transform_name}", exception="{str(e)}"'
                )

            # recreate the transform with the latest field definitions
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to create central collection transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'successfully created central collection transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                    f'failed to create central collection transform, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Update policy collection transforms for all enabled components
        # to include the 'account' field for remote Splunk deployment support
        #

        policy_components = []
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            policy_components.append("dsm")
        if vtenant_record.get("tenant_dhm_enabled") == 1:
            policy_components.append("dhm")
        if vtenant_record.get("tenant_mhm_enabled") == 1:
            policy_components.append("mhm")
        if vtenant_record.get("tenant_flx_enabled") == 1:
            policy_components.append("flx")
        if vtenant_record.get("tenant_wlk_enabled") == 1:
            policy_components.append("wlk")
        if vtenant_record.get("tenant_fqm_enabled") == 1:
            policy_components.append("fqm")

        for component in policy_components:

            policy_collections_to_update = [
                ("priority_policies", f"trackme_{component}_priority_policies"),
                ("sla_policies", f"trackme_{component}_sla_policies"),
                ("tags_policies", f"trackme_{component}_tags_policies"),
            ]

            for policy_label, dict_key in policy_collections_to_update:
                transform_name = f"{dict_key}_tenant_{tenant_id}"
                collection_name = f"kv_{dict_key}_tenant_{tenant_id}"
                transform_fields = collections_dict[dict_key]

                # delete the transform
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                            f'failed to delete the {policy_label} transform definition, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                            f'successfully deleted {policy_label} transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to delete the {policy_label} transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

                # create the transform with updated fields (includes account field)
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": definition_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                            f'create {policy_label} transform definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                            f'successfully created {policy_label} transform definition, transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to create the {policy_label} transform definition, transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # Update delayed entities inspector transforms for DSM/DHM
        # to include progressive backoff fields:
        # inspector_consecutive_no_data_count, inspector_last_data_found, inspector_backoff_multiplier
        #

        delayed_inspector_components = []
        if (
            vtenant_record.get("tenant_dsm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            delayed_inspector_components.append("dsm")
        if (
            vtenant_record.get("tenant_dhm_enabled") == 1
            and vtenant_record.get("tenant_replica") == 0
        ):
            delayed_inspector_components.append("dhm")

        for component in delayed_inspector_components:

            transform_name = (
                f"trackme_{component}_delayed_entities_inspector_tenant_{tenant_id}"
            )
            collection_name = (
                f"kv_trackme_{component}_delayed_entities_inspector_tenant_{tenant_id}"
            )
            transform_fields = collections_dict[
                f"trackme_{component}_delayed_entities_inspector"
            ]

            # delete the existing transform
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'failed to delete delayed inspector transform, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'successfully deleted delayed inspector transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                    f'failed to delete the delayed inspector transform, transform="{transform_name}", exception="{str(e)}"'
                )

            # recreate the transform with updated fields (includes backoff fields)
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": transform_name,
                "transform_fields": transform_fields,
                "collection_name": collection_name,
                "transform_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'create delayed inspector transform has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                        f'successfully created delayed inspector transform, transform="{transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", component="{component}", '
                    f'failed to create the delayed inspector transform, transform="{transform_name}", exception="{str(e)}"'
                )

        #
        # Create per-tenant shadow KV collections and transforms for each enabled component
        # Shadow collections store pre-computed, fully-enriched entity records for instant UI loading at scale
        #

        shadow_components = {
            "dsm": "tenant_dsm_enabled",
            "dhm": "tenant_dhm_enabled",
            "mhm": "tenant_mhm_enabled",
            "flx": "tenant_flx_enabled",
            "fqm": "tenant_fqm_enabled",
            "wlk": "tenant_wlk_enabled",
        }

        for component, enable_flag in shadow_components.items():

            if vtenant_record.get(enable_flag) != 1:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'component="{component}" is not enabled, skipping shadow collection creation'
                )
                continue

            shadow_base = f"trackme_{component}_shadow"
            transform_name = f"{shadow_base}_tenant_{tenant_id}"
            collection_name = f"kv_{shadow_base}_tenant_{tenant_id}"
            transform_fields = collections_dict[shadow_base]

            # Create the KVstore collection
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            kvstore_created = False
            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'create shadow KVstore collection has failed, component="{component}", collection="{collection_name}", '
                        f'response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'successfully created shadow KVstore collection, component="{component}", collection="{collection_name}"'
                    )
                    kvstore_created = True
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'failed to create shadow KVstore collection, component="{component}", collection="{collection_name}", exception="{str(e)}"'
                )

            # Create the transform definition
            if kvstore_created:
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                data = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": definition_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'create shadow transform definition has failed, component="{component}", transform="{transform_name}", '
                            f'response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'successfully created shadow transform definition, component="{component}", transform="{transform_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'failed to create shadow transform definition, component="{component}", transform="{transform_name}", exception="{str(e)}"'
                    )

        #
        # Create per-tenant score cache KV collection and transform
        # This common collection provides immediate visibility for false positive and manual score changes
        #

        score_cache_base = "trackme_common_score_cache"
        score_cache_transform_name = f"{score_cache_base}_tenant_{tenant_id}"
        score_cache_collection_name = f"kv_{score_cache_base}_tenant_{tenant_id}"
        score_cache_transform_fields = collections_dict[score_cache_base]

        # Create the KVstore collection
        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": score_cache_collection_name,
            "collection_acl": definition_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        score_cache_kvstore_created = False
        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'create score cache KVstore collection has failed, collection="{score_cache_collection_name}", '
                    f'response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'successfully created score cache KVstore collection, collection="{score_cache_collection_name}"'
                )
                score_cache_kvstore_created = True
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                f'failed to create score cache KVstore collection, collection="{score_cache_collection_name}", exception="{str(e)}"'
            )

        # Create the transform definition
        if score_cache_kvstore_created:
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
            data = {
                "tenant_id": tenant_id,
                "transform_name": score_cache_transform_name,
                "transform_fields": score_cache_transform_fields,
                "collection_name": score_cache_collection_name,
                "transform_acl": definition_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'create score cache transform definition has failed, transform="{score_cache_transform_name}", '
                        f'response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'successfully created score cache transform definition, transform="{score_cache_transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'failed to create score cache transform definition, transform="{score_cache_transform_name}", exception="{str(e)}"'
                )

        #
        # Fix WLK default thresholds regression (PR #685, fixed in PR #801):
        # The first default threshold was incorrectly seeded with metric_name="skipped_pct_last_24h"
        # (value=5, score=50) instead of "skipped_pct_last_4h" (value=5, score=50), creating a
        # duplicate skipped_pct_last_24h record and a missing skipped_pct_last_4h record.
        #

        if vtenant_record.get("tenant_wlk_enabled") == 1:

            wlk_thresholds_collection_name = f"kv_trackme_wlk_thresholds_tenant_{tenant_id}"

            try:
                wlk_thresholds_collection = service.kvstore[wlk_thresholds_collection_name]

                # Query all default threshold records
                default_records = wlk_thresholds_collection.data.query(
                    query=json.dumps({"object_id": "default"})
                )

                # Detect the regression: look for a duplicate skipped_pct_last_24h with value=5, score=50
                # (the correct skipped_pct_last_24h record has value=20, score=100)
                incorrect_record_key = None
                has_correct_skipped_pct_last_4h = False

                for record in default_records:
                    metric_name = record.get("metric_name")

                    if metric_name == "skipped_pct_last_24h":
                        try:
                            record_value = float(record.get("value", 0))
                            record_score = float(record.get("score", 0))
                        except (ValueError, TypeError):
                            continue
                        if record_value == 5 and record_score == 50:
                            incorrect_record_key = record.get("_key")

                    if metric_name == "skipped_pct_last_4h":
                        has_correct_skipped_pct_last_4h = True

                # Step 1: Delete the incorrect duplicate record if found
                if incorrect_record_key:
                    try:
                        wlk_thresholds_collection.data.delete_by_id(incorrect_record_key)
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'deleted incorrect duplicate WLK default threshold record (skipped_pct_last_24h with value=5, score=50), key="{incorrect_record_key}"'
                        )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'failed to delete incorrect WLK threshold record, key="{incorrect_record_key}", exception="{str(e)}"'
                        )

                # Step 2: Insert the correct skipped_pct_last_4h threshold if missing
                # (independent of step 1 to ensure idempotency after partial failures)
                if not has_correct_skipped_pct_last_4h:
                    try:
                        correct_record = {
                            "object_id": "default",
                            "metric_name": "skipped_pct_last_4h",
                            "value": 5,
                            "operator": ">",
                            "condition_true": False,
                            "score": 50,
                            "comment": "default threshold",
                            "mtime": time.time(),
                        }
                        wlk_thresholds_collection.data.insert(json.dumps(correct_record))
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'inserted correct WLK default threshold record (skipped_pct_last_4h, value=5, score=50)'
                        )
                    except Exception as e:
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                            f'failed to insert correct WLK threshold record, exception="{str(e)}"'
                        )

                if not incorrect_record_key and has_correct_skipped_pct_last_4h:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                        f'WLK default thresholds are correct, no fixup needed'
                    )

            except Exception as e:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2316, tenant_id="{tenant_id}", '
                    f'failed to process WLK thresholds fixup, collection="{wlk_thresholds_collection_name}", exception="{str(e)}"'
                )

        #
        # Update vtenant account configuration to add shadow_entity_threshold
        #

        update_vtenant_configuration(
            reqinfo,
            task_name,
            task_instance_id,
            tenant_id,
        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2316, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2317(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2317:
    - Adds shadow_enabled master switch to vtenant account configuration
    - Auto-detects whether shadow should be enabled based on entity count:
      if any enabled component's central collection has >= 1000 entities,
      shadow_enabled is set to 1; otherwise set to 0
    - shadow_entity_threshold is explicitly set to 1000 on all migrated tenants
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2317, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    query_string = {"tenant_id": tenant_id}

    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[0]
        vtenant_key = vtenant_record.get("_key")
    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'vtenant record not found, schema migration 2317 cannot proceed, exception="{str(e)}"'
        )

    if vtenant_key:

        #
        # Count entities in each enabled component's central collection
        # If any component has >= 1000 entities, enable shadow
        #

        shadow_threshold = 1000
        should_enable_shadow = False
        components = ["dsm", "dhm", "mhm", "flx", "fqm", "wlk"]

        for comp in components:
            # Check if component is enabled
            try:
                comp_enabled = int(vtenant_record.get(f"tenant_{comp}_enabled", 0))
            except (ValueError, TypeError):
                comp_enabled = 0

            if comp_enabled == 0:
                continue

            # Count records in the central collection using paginated _key-only queries
            collection_name = f"kv_trackme_{comp}_tenant_{tenant_id}"
            try:
                comp_collection = service.kvstore[collection_name]
                entity_count = 0
                chunk_size = 5000
                skip = 0

                while True:
                    rows = comp_collection.data.query(
                        fields="_key", limit=chunk_size, skip=skip
                    )
                    if not rows:
                        break
                    entity_count += len(rows)

                    # Early exit: we only need to know if >= threshold
                    if entity_count >= shadow_threshold:
                        should_enable_shadow = True
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                            f'component="{comp}" has {entity_count}+ entities (>= {shadow_threshold}), enabling shadow'
                        )
                        break

                    # Advance by actual count; stop only on an empty page (the
                    # >= threshold early-exit above still applies).
                    skip += len(rows)

                if should_enable_shadow:
                    break

                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'component="{comp}" has {entity_count} entities'
                )

            except Exception as e:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'failed to count entities in {collection_name}, exception="{str(e)}"'
                )

        #
        # Update vtenant configuration via REST endpoint
        #

        shadow_enabled_value = 1 if should_enable_shadow else 0

        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'schema migration 2317: setting shadow_enabled={shadow_enabled_value}, shadow_entity_threshold={shadow_threshold}'
        )

        try:
            url = f"{reqinfo['server_rest_uri']}/services/trackme/v2/vtenants/admin/update_tenant_shadow_config"
            header = {
                "Authorization": f"Splunk {reqinfo['session_key']}",
                "Content-Type": "application/json",
            }
            body = {
                "tenant_id": tenant_id,
                "shadow_enabled": shadow_enabled_value,
                "shadow_entity_threshold": shadow_threshold,
                "update_comment": f"Schema migration 2317: auto-detected shadow_enabled={shadow_enabled_value} based on entity counts",
            }

            response = requests.post(
                url,
                headers=header,
                data=json.dumps(body),
                verify=False,
                timeout=600,
            )

            if response.status_code in (200, 201, 204):
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'shadow configuration updated successfully via REST endpoint'
                )
            else:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'failed to update shadow configuration, status_code={response.status_code}, response="{response.text}"'
                )

        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'failed to update shadow configuration, exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2317, procedure terminated'
    )
    return True




def trackme_schema_upgrade_2319(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2319:
    - Create labels definition and label assignments KVstore collections per tenant
    - Seed default labels (blocked, under-review, in-progress, resolved, maintenance, acknowledged)
    - Auto-fix FLX hybrid trackers built from the OOTB "cribl_logstream_pipeline" use case:
      Cribl Stream renamed the pipeline dimension to "id" in their internal metrics, which
      broke the default SPL using "by group, pipeline" and ". pipeline" expressions. Any
      wrapper savedsearch whose SPL contains both "cribl.logstream.pipe.in_events" and
      "by group, pipeline" is patched in place by replacing "by group, pipeline" with
      "by group, id" and ". pipeline" with ". id".
    - Reduce SLA, Tags and Priority policy tracker frequency from */15 to 17 */12 (every 12h)
      to lower the global scheduled-search footprint.
    """

    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2319, tenant_id="{tenant_id}"'
    )

    # get the tenant record
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    query_string = {"tenant_id": tenant_id}

    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[0]
        vtenant_key = vtenant_record.get("_key")
    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'vtenant record not found, schema migration 2319 cannot proceed, exception="{str(e)}"'
        )

    if vtenant_key:

        # get permissions
        tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(
            vtenant_record
        )

        # TrackMe sharing level
        trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        ko_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": trackme_default_sharing,
            "perms.write": tenant_roles_write_perms,
            "perms.read": tenant_roles_read_perms,
        }

        #
        # Create labels collections
        #

        label_collections = [
            ("trackme_labels", f"kv_trackme_labels_tenant_{tenant_id}"),
            ("trackme_label_assignments", f"kv_trackme_label_assignments_tenant_{tenant_id}"),
        ]

        for collection_base, collection_name in label_collections:

            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
            data = {
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "collection_acl": ko_acl,
                "owner": vtenant_record.get("tenant_owner"),
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'create KVstore collection has failed, collection="{collection_name}", '
                        f'response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'successfully created KVstore collection, collection="{collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                    f'failed to create the KVstore collection, collection="{collection_name}", exception="{str(e)}"'
                )

        #
        # Seed default labels (from collections_data.default_labels)
        #

        labels_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        try:
            labels_collection = service.kvstore[labels_collection_name]

            # Check existing labels to avoid duplicates
            existing = list(labels_collection.data.query())
            existing_names = {l.get("label_name", "").lower() for l in existing}

            now = time.time()
            created_count = 0
            for default_label in default_labels:
                if default_label["label_name"].lower() not in existing_names:
                    label_record = {
                        "label_name": default_label["label_name"],
                        "label_color": default_label["label_color"],
                        "label_description": default_label["label_description"],
                        "label_order": default_label["label_order"],
                        "is_default": "1",
                        "created_by": "system",
                        "ctime": now,
                        "mtime": now,
                    }
                    labels_collection.data.insert(json.dumps(label_record))
                    created_count += 1

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                f'seeded {created_count} default labels'
            )

        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                f'failed to seed default labels, exception="{str(e)}"'
            )

        #
        # Create variable delay templates collection (per-tenant customisable
        # quick templates for the DSM/DHM variable delay slot editors). On
        # upgrade, the collection is simply empty — consumers fall back to
        # the hardcoded factory defaults in slotTemplates.ts, so existing
        # tenants see no UX change until an admin actively customises the
        # templates via the new "Manage: Variable delay templates" modal.
        #
        variable_delay_templates_collection_name = (
            f"kv_trackme_common_variable_delay_templates_tenant_{tenant_id}"
        )

        url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
        data = {
            "tenant_id": tenant_id,
            "collection_name": variable_delay_templates_collection_name,
            "collection_acl": ko_acl,
            "owner": vtenant_record.get("tenant_owner"),
        }

        try:
            response = requests.post(
                url,
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 202, 204):
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                    f'create KVstore collection has failed, collection="{variable_delay_templates_collection_name}", '
                    f'response.status_code="{response.status_code}", response.text="{response.text}"'
                )
            else:
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                    f'successfully created KVstore collection, collection="{variable_delay_templates_collection_name}"'
                )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                f'failed to create the KVstore collection, collection="{variable_delay_templates_collection_name}", exception="{str(e)}"'
            )

        #
        # Auto-fix FLX hybrid trackers built from the OOTB "cribl_logstream_pipeline" use case
        #
        # Cribl Stream renamed the "pipeline" dimension to "id" in the internal metrics
        # (cribl.logstream.pipe.*), which broke the default SPL shipped in previous releases.
        # We detect the exact signature of the OOTB wrapper search in each FLX hybrid tracker
        # and patch it in place to use the new dimension name.
        #
        if vtenant_record.get("tenant_flx_enabled") == 1:

            collection_trackers_name = (
                f"kv_trackme_flx_hybrid_trackers_tenant_{tenant_id}"
            )

            try:
                collection_trackers = service.kvstore[collection_trackers_name]
                trackers_records = collection_trackers.data.query()
            except Exception as e:
                trackers_records = []
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                    f'failed to query FLX hybrid trackers collection="{collection_trackers_name}", exception="{str(e)}"'
                )

            cribl_wrappers_to_process = []

            for tracker_record in trackers_records:
                try:
                    tracker_kos = json.loads(
                        tracker_record.get("knowledge_objects") or "{}"
                    )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'failed to parse knowledge_objects for tracker_record="{tracker_record.get("tracker_name")}", exception="{str(e)}"'
                    )
                    continue

                for tracker_report in tracker_kos.get("reports", []):
                    if "_wrapper_" in tracker_report:
                        cribl_wrappers_to_process.append(tracker_report)

            for tracker_name in cribl_wrappers_to_process:

                try:
                    tracker_current = service.saved_searches[tracker_name]
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'tracker_name="{tracker_name}", failed to get the tracker definition, exception="{str(e)}"'
                    )
                    continue

                tracker_current_search = tracker_current.content.get("search") or ""
                tracker_current_earliest_time = tracker_current.content.get(
                    "dispatch.earliest_time"
                )
                tracker_current_latest_time = tracker_current.content.get(
                    "dispatch.latest_time"
                )

                # Only touch searches that match the exact OOTB Cribl pipeline signature:
                # they must reference the cribl.logstream.pipe.in_events metric AND
                # still use the legacy "by group, pipeline" grouping. This signature
                # check is also what makes the migration idempotent: once patched the
                # SPL no longer contains "by group, pipeline" and subsequent runs skip
                # the record here.
                if (
                    "cribl.logstream.pipe.in_events" not in tracker_current_search
                    or "by group, pipeline" not in tracker_current_search
                ):
                    continue

                # Apply the two substitutions requested by Cribl's dimension rename.
                tracker_new_search = tracker_current_search.replace(
                    "by group, pipeline", "by group, id"
                )
                tracker_new_search = tracker_new_search.replace(". pipeline", ". id")

                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": tracker_name,
                    "report_search": tracker_new_search,
                    "earliest_time": tracker_current_earliest_time,
                    "latest_time": tracker_current_latest_time,
                }

                try:
                    response = requests.post(
                        url,
                        headers={
                            "Authorization": f'Splunk {reqinfo["session_key"]}'
                        },
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                            f'failed to update Cribl pipeline tracker, tracker_name="{tracker_name}", '
                            f'response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                            f'successfully patched Cribl pipeline tracker (pipeline->id dimension rename), tracker_name="{tracker_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'exception while updating Cribl pipeline tracker, tracker_name="{tracker_name}", exception="{str(e)}"'
                    )

        #
        # Reduce SLA / Tags / Priority policy tracker frequency from every 15 minutes
        # to every 12 hours.  These policies manage relatively static content that does
        # not need to run every 15 minutes; running twice a day is sufficient and greatly
        # reduces the global scheduled-search footprint.
        #
        # Only update trackers whose current cron frequency is less than 20 minutes
        # (1200 seconds) to respect any user-customized schedules.
        #
        max_frequency_seconds = 1200  # 20 minutes
        policy_tracker_types = ["tags_tracker", "priority_tracker", "sla_tracker"]
        components = ["dsm", "dhm", "mhm", "flx", "fqm", "wlk"]

        for component in components:
            for tracker_type in policy_tracker_types:
                report_name = f"trackme_{component}_{tracker_type}_tenant_{tenant_id}"

                try:
                    report_obj = service.saved_searches[report_name]
                except Exception:
                    # Report does not exist (component may never have been enabled)
                    continue

                current_cron = report_obj.content.get("cron_schedule", "")

                # Check the effective frequency — only update if running more
                # frequently than every 20 minutes (preserves user customizations)
                try:
                    current_frequency = cron_to_seconds(current_cron)
                except Exception:
                    # Cannot parse the cron expression — skip
                    continue

                if current_frequency >= max_frequency_seconds:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'skipping policy tracker update, report="{report_name}", '
                        f'current_cron="{current_cron}", current_frequency={current_frequency}s (>= {max_frequency_seconds}s threshold)'
                    )
                    continue

                # Generate a randomized every-12-hour cron schedule
                new_policy_cron = f"{random.randint(0, 59)} */12 * * *"

                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/update_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": report_name,
                    "cron_schedule": new_policy_cron,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                            f'failed to update policy tracker cron schedule, report="{report_name}", '
                            f'response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                            f'updated policy tracker cron schedule, report="{report_name}", '
                            f'old_cron="{current_cron}", new_cron="{new_policy_cron}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2319, tenant_id="{tenant_id}", '
                        f'failed to update policy tracker cron schedule, report="{report_name}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2319, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2322(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    Schema migration 2322:
    - Backfills the three new ML Outliers tenant-level fields introduced in 2.3.22
      so existing tenants behave identically after upgrade.
    - Backfill is gated on key absence (`field not in vtenant_record`), not on
      empty-value detection, so an admin-set empty string (a legitimate value
      for filter_expression and volume_kpi, both of which mean "no override")
      is never re-written.
    - Migrated defaults preserve current behaviour (all priorities, no filter,
      inherit global volume KPI). New tenants created via the wizard get a
      narrower default (critical,high) applied at creation time, not here.
    - Recreates the per-tenant `trackme_<component>_outliers_entity_data_tenant_<tid>`
      lookup transforms for every component that has outliers (DSM, DHM, FLX, FQM,
      WLK) so the three new cache fields (`lastIsOutlierReason`,
      `lastIsOutlierReason_models`, `lastIsOutlierReason_mtime`) become accessible
      from SPL via `inputlookup` / `lookup`. The KV collection itself does not
      need migrating — KV records simply gain the new fields on the next outliers
      tracker write — but the transform's `fields_list` is captured at create
      time and must be refreshed on existing tenants.
    """

    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2322, tenant_id="{tenant_id}"'
    )

    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    query_string = {"tenant_id": tenant_id}

    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[0]
        vtenant_key = vtenant_record.get("_key")
    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'vtenant record not found, schema migration 2322 cannot proceed, exception="{str(e)}"'
        )

    if vtenant_key:

        # Migrated defaults preserve prior behaviour: all priorities are eligible,
        # no filter expression, fall back to the global default volume KPI.
        # Keys use the `tenant_` prefix to match the KV record schema —
        # vtenant rows store flags as `tenant_mloutliers`, `tenant_mloutliers_allowlist`,
        # etc. (the unprefixed names live only in collections_data.vtenant_account_default
        # and trackme_vtenants.conf.spec, which describe the wizard payload, not the
        # persisted KV record).
        migrated_defaults = {
            "tenant_mloutliers_priority_filter": "critical,high,medium,low",
            "tenant_mloutliers_filter_expression": "",
            "tenant_mloutliers_volume_kpi": "",
        }

        backfilled = []
        for field, default_value in migrated_defaults.items():
            # Gate on key absence rather than empty-value detection.
            # `""` is a legitimate admin-set value for filter_expression and
            # volume_kpi (it means "no filter" / "inherit global default"),
            # so a set-but-empty key must NOT be re-written by the migration.
            if field not in vtenant_record:
                vtenant_record[field] = default_value
                backfilled.append(field)

        if backfilled:
            try:
                collection_vtenants.data.update(
                    str(vtenant_key), json.dumps(vtenant_record)
                )
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'schema migration 2322: backfilled fields={backfilled}'
                )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'schema migration 2322 failed to update vtenant record, exception="{str(e)}"'
                )
        else:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2322: no backfill needed, all ML Outliers tenant fields already present'
            )

        #
        # Refresh outliers entity_data transforms for the three new cache fields
        # (lastIsOutlierReason, lastIsOutlierReason_models, lastIsOutlierReason_mtime).
        # The transform's `fields_list` is fixed at create time, so existing
        # tenants need a delete + recreate to expose the new columns to SPL.
        # MHM is excluded because it has no outliers entity_data collection
        # (matches the gating in trackme_rest_handler_component_user.py).
        #
        outlier_components_enabled = []
        for component, enabled_field in (
            ("dsm", "tenant_dsm_enabled"),
            ("dhm", "tenant_dhm_enabled"),
            ("flx", "tenant_flx_enabled"),
            ("fqm", "tenant_fqm_enabled"),
            ("wlk", "tenant_wlk_enabled"),
        ):
            try:
                if int(vtenant_record.get(enabled_field, 0)) == 1:
                    outlier_components_enabled.append(component)
            except (TypeError, ValueError):
                # tenant_<component>_enabled is missing or non-numeric — skip
                continue

        if outlier_components_enabled:
            transform_acl = {
                "owner": vtenant_record.get("tenant_owner"),
                "sharing": "app",
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": vtenant_record.get("tenant_roles_user"),
            }

            for component in outlier_components_enabled:
                object_name = f"trackme_{component}_outliers_entity_data"
                transform_name = f"{object_name}_tenant_{tenant_id}"
                collection_name = f"kv_{object_name}_tenant_{tenant_id}"

                try:
                    transform_fields = collections_dict[object_name]
                except KeyError:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                        f'schema migration 2322: collections_dict has no entry for "{object_name}", skipping transform refresh'
                    )
                    continue

                # Delete the existing transform definition (idempotent — a 404
                # / "not found" response is acceptable, the recreate below
                # restores it from the current collections_dict definition).
                delete_url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                delete_payload = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                }
                try:
                    delete_response = requests.post(
                        delete_url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(delete_payload),
                        verify=False,
                        timeout=600,
                    )
                    if delete_response.status_code not in (200, 201, 202, 204, 404):
                        get_effective_logger().warning(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                            f'schema migration 2322: delete_kvtransform returned an unexpected status, '
                            f'transform="{transform_name}", status_code={delete_response.status_code}, '
                            f'response.text="{delete_response.text}" (continuing with recreate)'
                        )
                except Exception as e:
                    get_effective_logger().warning(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                        f'schema migration 2322: delete_kvtransform raised an exception, '
                        f'transform="{transform_name}", exception="{str(e)}" (continuing with recreate)'
                    )

                # Recreate with the updated fields_list
                create_url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                create_payload = {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": collection_name,
                    "transform_acl": transform_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }
                try:
                    create_response = requests.post(
                        create_url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(create_payload),
                        verify=False,
                        timeout=600,
                    )
                    if create_response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                            f'schema migration 2322: create_kvtransform failed, transform="{transform_name}", '
                            f'status_code={create_response.status_code}, response.text="{create_response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                            f'schema migration 2322: refreshed outliers entity_data transform="{transform_name}" with new lastIsOutlierReason* fields'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                        f'schema migration 2322: create_kvtransform raised an exception, '
                        f'transform="{transform_name}", exception="{str(e)}"'
                    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2322, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2400(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    # Register the object summary in the vtenant collection
    collection_vtenants_name = "kv_trackme_virtual_tenants"
    collection_vtenants = service.kvstore[collection_vtenants_name]

    # Define the KV query search string
    query_string = {
        "tenant_id": tenant_id,
    }

    # log
    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2400, tenant_id="{tenant_id}"'
    )

    objects_to_process = []

    # get the tenant record
    try:
        vtenant_record = collection_vtenants.data.query(query=json.dumps(query_string))[
            0
        ]
        vtenant_key = vtenant_record.get("_key")
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was successfully found in the collection, query_string="{query_string}"'
        )

    except Exception as e:
        vtenant_key = None
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, The vtenant_key was not found in the collection, query_string="{query_string}"'
        )

    if vtenant_key:
        # ─────────────────────────────────────────────────────────────────
        # Vtenant account schema reconciliation
        #
        # The maintain_vtenant_account endpoint compares the tenant's
        # current vtenant_account record against vtenant_account_default
        # and:
        #   - keeps existing keys that still exist in the default
        #   - adds missing keys from the default
        #   - drops keys that no longer exist in the default
        #
        # Calling it here ensures existing tenants pick up the unified
        # `ai_components_advisor_*` fields and shed the old per-component
        # `ai_feedlifecycle_*` / `ai_flxthreshold_*` / `ai_wlkadvisor_*` /
        # `ai_fqmadvisor_*` / `ai_mhmadvisor_*` / `ai_feed_lifecycle_allow_decommission`
        # families on the next tracker-health cycle, rather than waiting
        # for the periodic maintenance pass to drift in.
        #
        # No-op for new tenants whose record was just created from
        # vtenant_account_default at tenant creation time.
        # ─────────────────────────────────────────────────────────────────
        try:
            update_vtenant_configuration(
                reqinfo,
                task_name,
                task_instance_id,
                tenant_id,
            )
        except Exception as e:
            get_effective_logger().warning(
                f'task="{task_name}", task_instance_id={task_instance_id}, '
                f'tenant_id="{tenant_id}", non-fatal: failed to reconcile '
                f'vtenant_account schema during 2400 migration, exception="{e}"'
            )

        # check components and add accordingly
        if vtenant_record.get("tenant_dsm_enabled") == 1:
            objects_to_process.append(
                "trackme_dsm_outliers_mladvisor_tracker_tenant_%s" % tenant_id
            )

        if vtenant_record.get("tenant_dhm_enabled") == 1:
            objects_to_process.append(
                "trackme_dhm_outliers_mladvisor_tracker_tenant_%s" % tenant_id
            )

        if vtenant_record.get("tenant_flx_enabled") == 1:
            objects_to_process.append(
                "trackme_flx_outliers_mladvisor_tracker_tenant_%s" % tenant_id
            )

        for report_name in objects_to_process:
            # create the report
            component = None

            if report_name.startswith("trackme_dsm"):
                component = "dsm"
            elif report_name.startswith("trackme_dhm"):
                component = "dhm"
            elif report_name.startswith("trackme_flx"):
                component = "flx"

            report_search = (
                '| trackmesplkoutliersmladvisorhelper tenant_id="%s" component="%s"'
                % (tenant_id, component)
            )
            report_properties = {
                "description": "This scheduled report performs automated AI-powered ML model inspection for the tenant",
                "is_scheduled": True,
                "cron_schedule": "0 2-5 * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            # for read permissions, concatenate admin and guest
            tenant_roles_read_perms = "%s,%s" % (
                str(vtenant_record.get("tenant_roles_admin")),
                str(vtenant_record.get("tenant_roles_user")),
            )

            # Note: no pre-delete here. These mladvisor reports are
            # net-new in 2.4.0, so a delete on a fresh 2.3.24 → 2.4.0
            # upgrade would always fail with "No such entity" and
            # pollute the log. On re-runs the create_report REST
            # handler returns HTTP 202 ("already exists, skipping
            # creation"), which the (200, 201, 202, 204) success set
            # below treats as a no-op.

            # create the report
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create the report definition, report="{report_name}", exception="{str(e)}"'
                )

    # Create Feed Lifecycle Advisor saved searches for DSM and DHM
    feedlifecycle_reports = []

    if vtenant_key:
        try:
            if int(vtenant_record.get("tenant_dsm_enabled", 0)) == 1:
                feedlifecycle_reports.append(
                    "trackme_dsm_feed_lifecycle_advisor_tracker_tenant_%s" % tenant_id
                )
        except (ValueError, TypeError):
            pass

        try:
            if int(vtenant_record.get("tenant_dhm_enabled", 0)) == 1:
                feedlifecycle_reports.append(
                    "trackme_dhm_feed_lifecycle_advisor_tracker_tenant_%s" % tenant_id
                )
        except (ValueError, TypeError):
            pass

        for report_name in feedlifecycle_reports:
            component = "dsm" if report_name.startswith("trackme_dsm") else "dhm"

            report_search = (
                '| trackmesplkfeedlifecycleadvisorhelper tenant_id="%s" component="%s"'
                % (tenant_id, component)
            )
            report_properties = {
                "description": "This scheduled report performs automated AI-powered Feed Lifecycle Advisor review for the tenant",
                "is_scheduled": True,
                "cron_schedule": "0 5-8 * * *",
                "dispatch.earliest_time": "-5m",
                "dispatch.latest_time": "now",
                "schedule_window": "5",
            }

            tenant_roles_read_perms = "%s,%s" % (
                str(vtenant_record.get("tenant_roles_admin")),
                str(vtenant_record.get("tenant_roles_user")),
            )

            # Note: no pre-delete here. See the mladvisor block above
            # for the rationale — these feedlifecycle reports are
            # net-new in 2.4.0 and the create handler is idempotent
            # via HTTP 202 on duplicate.

            # create the report
            report_acl = {
                "owner": str(vtenant_record.get("tenant_owner")),
                "sharing": "app",
                "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                "perms.read": str(tenant_roles_read_perms),
            }
            url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
            data = {
                "tenant_id": tenant_id,
                "report_name": report_name,
                "report_search": report_search,
                "report_properties": report_properties,
                "report_acl": report_acl,
            }

            try:
                response = requests.post(
                    url,
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(data),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create feedlifecycle report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created feedlifecycle report definition, report="{report_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create feedlifecycle report definition, report="{report_name}", exception="{str(e)}"'
                )

    # Create FLX Threshold Advisor saved search (FLX only)
    if vtenant_key:
        try:
            if int(vtenant_record.get("tenant_flx_enabled", 0)) == 1:
                flxthreshold_report_name = (
                    "trackme_flx_threshold_advisor_tracker_tenant_%s" % tenant_id
                )

                flxthreshold_report_search = (
                    '| trackmesplkflxthresholdadvisorhelper tenant_id="%s" component="flx"'
                    % tenant_id
                )
                flxthreshold_report_properties = {
                    "description": "This scheduled report performs automated AI-powered FLX Threshold Advisor review for the tenant",
                    "is_scheduled": True,
                    "cron_schedule": "0 9-12 * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }

                tenant_roles_read_perms = "%s,%s" % (
                    str(vtenant_record.get("tenant_roles_admin")),
                    str(vtenant_record.get("tenant_roles_user")),
                )

                # Note: no pre-delete here. See the mladvisor block above
                # for the rationale — this flxthreshold report is net-new
                # in 2.4.0 and the create handler is idempotent via
                # HTTP 202 on duplicate.

                # create the report
                flxthreshold_report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                    "perms.read": str(tenant_roles_read_perms),
                }
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": flxthreshold_report_name,
                    "report_search": flxthreshold_report_search,
                    "report_properties": flxthreshold_report_properties,
                    "report_acl": flxthreshold_report_acl,
                }

                try:
                    response = requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create flxthreshold report definition has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )
                    else:
                        get_effective_logger().info(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created flxthreshold report definition, report="{flxthreshold_report_name}"'
                        )
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create flxthreshold report definition, report="{flxthreshold_report_name}", exception="{str(e)}"'
                    )
        except (ValueError, TypeError):
            pass

    # Create WLK Component Health Advisor saved search (WLK only)
    if vtenant_key:
        try:
            if int(vtenant_record.get("tenant_wlk_enabled", 0)) == 1:
                componenthealth_wlk_report_name = (
                    "trackme_wlk_component_health_advisor_tracker_tenant_%s" % tenant_id
                )
                componenthealth_wlk_report_search = (
                    '| trackmesplkcomponenthealthadvisorhelper tenant_id="%s" component="wlk"'
                    % tenant_id
                )
                componenthealth_wlk_report_properties = {
                    "description": "This scheduled report performs automated AI-powered WLK Component Health Advisor review for the tenant",
                    "is_scheduled": True,
                    "cron_schedule": "0 9-12 * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }
                tenant_roles_read_perms = "%s,%s" % (
                    str(vtenant_record.get("tenant_roles_admin")),
                    str(vtenant_record.get("tenant_roles_user")),
                )
                # Note: no pre-delete here. See the mladvisor block above
                # for the rationale — this WLK component-health report is
                # net-new in 2.4.0 and the create handler is idempotent
                # via HTTP 202 on duplicate.
                componenthealth_wlk_report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                    "perms.read": str(tenant_roles_read_perms),
                }
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": componenthealth_wlk_report_name,
                    "report_search": componenthealth_wlk_report_search,
                    "report_properties": componenthealth_wlk_report_properties,
                    "report_acl": componenthealth_wlk_report_acl,
                }
                try:
                    response = requests.post(url, headers={"Authorization": f'Splunk {reqinfo["session_key"]}'}, data=json.dumps(data), verify=False, timeout=600)
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create wlk component health report failed, status="{response.status_code}"')
                    else:
                        get_effective_logger().info(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created wlk component health report, report="{componenthealth_wlk_report_name}"')
                except Exception as e:
                    get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create wlk component health report, exception="{str(e)}"')
        except (ValueError, TypeError):
            pass

    # Create dedicated FQM Advisor saved search (FQM has been split out of the Component
    # Health Advisor into its own dictionary-aware advisor — see trackme_libs_ai_fqm_advisor.py).
    # On upgrade, also clean up the old Component-Health-FQM saved search if it exists.
    if vtenant_key:
        try:
            if int(vtenant_record.get("tenant_fqm_enabled", 0)) == 1:
                # Cleanup: remove the old Component-Health-based FQM saved search if it
                # lingers from a previous install — idempotent if it doesn't exist.
                legacy_fqm_componenthealth_report_name = (
                    "trackme_fqm_component_health_advisor_tracker_tenant_%s" % tenant_id
                )
                try:
                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_report'
                    data = {"tenant_id": tenant_id, "report_name": legacy_fqm_componenthealth_report_name}
                    requests.post(
                        url,
                        headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                        data=json.dumps(data),
                        verify=False,
                        timeout=600,
                    )
                except Exception as e:
                    get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to delete legacy fqm component health report, exception="{str(e)}"')

                # Create the new dedicated FQM Advisor saved search.
                fqmadvisor_report_name = (
                    "trackme_fqm_advisor_tracker_tenant_%s" % tenant_id
                )
                fqmadvisor_report_search = (
                    '| trackmesplkfqmadvisorhelper tenant_id="%s" component="fqm"'
                    % tenant_id
                )
                fqmadvisor_report_properties = {
                    "description": "This scheduled report performs automated AI-powered FQM Advisor review for the tenant (dictionary + regex + threshold calibration)",
                    "is_scheduled": True,
                    "cron_schedule": "0 13-16 * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }
                tenant_roles_read_perms = "%s,%s" % (
                    str(vtenant_record.get("tenant_roles_admin")),
                    str(vtenant_record.get("tenant_roles_user")),
                )
                # Note: no pre-delete here. See the mladvisor block above
                # for the rationale — the new fqm_advisor report is
                # net-new in 2.4.0 and the create handler is idempotent
                # via HTTP 202 on duplicate. (The legacy
                # fqm_component_health cleanup just above is a separate
                # one-time delete that *does* target a real artefact
                # from an earlier 2.4.0 beta; it stays.)
                fqmadvisor_report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                    "perms.read": str(tenant_roles_read_perms),
                }
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": fqmadvisor_report_name,
                    "report_search": fqmadvisor_report_search,
                    "report_properties": fqmadvisor_report_properties,
                    "report_acl": fqmadvisor_report_acl,
                }
                try:
                    response = requests.post(url, headers={"Authorization": f'Splunk {reqinfo["session_key"]}'}, data=json.dumps(data), verify=False, timeout=600)
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create fqm advisor report failed, status="{response.status_code}"')
                    else:
                        get_effective_logger().info(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created fqm advisor report, report="{fqmadvisor_report_name}"')
                except Exception as e:
                    get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create fqm advisor report, exception="{str(e)}"')
        except (ValueError, TypeError):
            pass

    # Create MHM Component Health Advisor saved search (MHM only)
    if vtenant_key:
        try:
            if int(vtenant_record.get("tenant_mhm_enabled", 0)) == 1:
                componenthealth_mhm_report_name = (
                    "trackme_mhm_component_health_advisor_tracker_tenant_%s" % tenant_id
                )
                componenthealth_mhm_report_search = (
                    '| trackmesplkcomponenthealthadvisorhelper tenant_id="%s" component="mhm"'
                    % tenant_id
                )
                componenthealth_mhm_report_properties = {
                    "description": "This scheduled report performs automated AI-powered MHM Component Health Advisor review for the tenant",
                    "is_scheduled": True,
                    "cron_schedule": "0 9-12 * * *",
                    "dispatch.earliest_time": "-5m",
                    "dispatch.latest_time": "now",
                    "schedule_window": "5",
                }
                tenant_roles_read_perms = "%s,%s" % (
                    str(vtenant_record.get("tenant_roles_admin")),
                    str(vtenant_record.get("tenant_roles_user")),
                )
                # Note: no pre-delete here. See the mladvisor block above
                # for the rationale — this MHM component-health report is
                # net-new in 2.4.0 and the create handler is idempotent
                # via HTTP 202 on duplicate.
                componenthealth_mhm_report_acl = {
                    "owner": str(vtenant_record.get("tenant_owner")),
                    "sharing": "app",
                    "perms.write": str(vtenant_record.get("tenant_roles_admin")),
                    "perms.read": str(tenant_roles_read_perms),
                }
                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_report'
                data = {
                    "tenant_id": tenant_id,
                    "report_name": componenthealth_mhm_report_name,
                    "report_search": componenthealth_mhm_report_search,
                    "report_properties": componenthealth_mhm_report_properties,
                    "report_acl": componenthealth_mhm_report_acl,
                }
                try:
                    response = requests.post(url, headers={"Authorization": f'Splunk {reqinfo["session_key"]}'}, data=json.dumps(data), verify=False, timeout=600)
                    if response.status_code not in (200, 201, 202, 204):
                        get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", create mhm component health report failed, status="{response.status_code}"')
                    else:
                        get_effective_logger().info(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", successfully created mhm component health report, report="{componenthealth_mhm_report_name}"')
                except Exception as e:
                    get_effective_logger().error(f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", failed to create mhm component health report, exception="{str(e)}"')
        except (ValueError, TypeError):
            pass

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", schema migration 2400, procedure terminated'
    )
    return True


def trackme_schema_upgrade_2401(
    reqinfo, tenant_id, source_version, target_version, task_name, task_instance_id
):
    """
    2.4.1 schema upgrade. Several independent concerns:

    A. **Smart Status decommission** (PR #1629, deferred from the reverted 2.4.1
       bump — see PR #1643/#1646). Runs for EVERY tenant regardless of enabled
       components: strips the orphan ``trackme_smart_status`` alert action out of
       TrackMe-managed alerts and drops the per-tenant smartstatus throttle KV
       collection + transform. The alert-action code itself was already removed
       in PR #1629; this clears the inert references it left behind. Idempotent.

    B. **Introduce the DHM ``asset`` field** (DHM-enabled tenants only):
       1. Refresh the central DHM lookup transform (``trackme_dhm_tenant_<tid>``)
          so its ``fields_list`` picks up the new ``asset`` field from
          ``collections_data.py`` — making ``asset`` visible to ``| lookup`` /
          ``| inputlookup`` on existing tenants (new tenants get it at creation).
          Delete-then-recreate via the admin REST endpoints, mirroring 2316.
       2. Backfill ``asset`` on existing entity records. The field is a
          lowercase, deduplicated, sorted multivalue set of every known variation
          of the endpoint — the object (verbatim), the alias, the bare value with
          any ``key:host|`` prefix stripped, and the short hostname when a value
          is an FQDN. It is recomputed on every tracker cycle by the SPL
          ``trackme_dhm_build_asset`` macro; this seeds it on already-stored
          records. Idempotent — records whose stored asset already matches are
          left untouched. Uses the same build_dhm_asset_list() helper as the live
          SPL path so storage is identical.

    D. **Delay/latency Threshold Intent Lock** (DSM/DHM-enabled tenants): create
       the per-tenant threshold-intent ledger collection + transform
       (``kv_trackme_{component}_threshold_intent_tenant_<tid>``) and refresh the
       main DSM/DHM transform so the new ``data_max_delay_allowed_locked`` /
       ``data_max_lag_allowed_locked`` fields are visible to ``| lookup``.
       Implemented as a self-contained block placed before Concern B's DHM-only
       early return so DSM-only tenants are provisioned too. Idempotent. New
       tenants get all of this at creation via ``collections_list_{dsm,dhm}``.
    """
    # get service
    service = client.connect(
        host=reqinfo.get("server_rest_host", "127.0.0.1"),
        owner="nobody",
        app="trackme",
        port=reqinfo["server_rest_port"],
        token=reqinfo["session_key"],
        timeout=600,
    )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, Starting function trackme_schema_upgrade_2401, tenant_id="{tenant_id}"'
    )

    # check the tenant has DHM enabled — no-op otherwise
    collection_vtenants = service.kvstore["kv_trackme_virtual_tenants"]
    try:
        vtenant_record = collection_vtenants.data.query(
            query=json.dumps({"tenant_id": tenant_id})
        )[0]
    except Exception:
        get_effective_logger().warning(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f"vtenant record not found, skipping DHM asset migration"
        )
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Concern A — Smart Status decommission (ALL tenants, any components).
    # Strip the orphan trackme_smart_status alert action out of TrackMe-managed
    # alerts and drop the per-tenant smartstatus throttle KV collection +
    # transform. The action code was removed in PR #1629; this clears the inert
    # references it left behind.
    # ─────────────────────────────────────────────────────────────────────

    # A.1 — strip trackme_smart_status from every TrackMe-managed alert. Iterate
    # the tenant's `alerts` list only (never touch saved-searches not owned by
    # TrackMe — they may be third-party content).
    alert_objects_raw = vtenant_record.get("tenant_alert_objects", None)
    alerts_list = []
    if alert_objects_raw:
        try:
            alert_objects = json.loads(alert_objects_raw)
            if isinstance(alert_objects, dict):
                alerts_list = alert_objects.get("alerts", []) or []
        except Exception:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f"schema migration 2401, no parseable tenant_alert_objects, nothing to strip"
            )
            alerts_list = []

    smartstatus_stripped_count = 0
    for alert_name in alerts_list:
        try:
            alert_current = service.saved_searches[alert_name]
        except Exception:
            # Alert no longer exists — skip silently.
            continue

        try:
            actions = alert_current.content.get("actions", "") or ""
            if isinstance(actions, str):
                actions_list = [a.strip() for a in actions.split(",") if a.strip()]
            elif isinstance(actions, list):
                actions_list = list(actions)
            else:
                actions_list = []

            if "trackme_smart_status" not in actions_list:
                continue

            new_actions_csv = ",".join(
                a for a in actions_list if a != "trackme_smart_status"
            )

            # Blank every action.trackme_smart_status.* param — inert once the
            # action is no longer enabled; empty-string values clear them.
            params_to_blank = {
                k: ""
                for k in list(alert_current.content.keys())
                if k.startswith("action.trackme_smart_status.")
                or k == "action.trackme_smart_status"
            }

            update_kwargs = {"actions": new_actions_csv}
            update_kwargs.update(params_to_blank)
            alert_current.update(**update_kwargs)
            smartstatus_stripped_count += 1

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2401, stripped trackme_smart_status action from alert="{alert_name}"'
            )
        except Exception as e:
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2401, failed to update alert="{alert_name}", exception="{str(e)}"'
            )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
        f"schema migration 2401, stripped trackme_smart_status from {smartstatus_stripped_count} alert(s)"
    )

    # A.2 — drop the per-tenant Smart Status throttle KV collection and its
    # transform via the admin REST endpoints, but ONLY if they still exist.
    # The collection was created by the old migration 2095; tenants that never
    # ran that creation (or were created after it was removed) don't have it,
    # and the delete endpoints return a noisy 500 "No such entity" for a missing
    # target. Pre-check existence so the absent-target path stays silent.
    smartstatus_collection_name = (
        f"kv_trackme_common_smartstatus_alert_action_last_seen_activity_tenant_{tenant_id}"
    )
    smartstatus_transform_name = (
        f"trackme_common_smartstatus_alert_action_last_seen_activity_tenant_{tenant_id}"
    )

    # Targeted existence checks (a GET for the specific name, not a list call —
    # reliable regardless of how many collections/transforms the tenant has).
    # On a check failure we conservatively treat the target as absent and skip
    # the drop: the orphan is inert, and skipping avoids the 500 noise this
    # guard exists to remove.
    try:
        smartstatus_transform_exists = (
            smartstatus_transform_name in service.confs["transforms"]
        )
    except Exception as e:
        smartstatus_transform_exists = False
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'schema migration 2401, could not check smartstatus transform existence, treating as absent, exception="{str(e)}"'
        )
    try:
        smartstatus_collection_exists = smartstatus_collection_name in service.kvstore
    except Exception as e:
        smartstatus_collection_exists = False
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'schema migration 2401, could not check smartstatus collection existence, treating as absent, exception="{str(e)}"'
        )

    # drop the transform first (it references the collection) — only if present
    if smartstatus_transform_exists:
        try:
            response = requests.post(
                f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform',
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(
                    {"tenant_id": tenant_id, "transform_name": smartstatus_transform_name}
                ),
                verify=False,
                timeout=600,
            )
            if response.status_code in (200, 201, 202, 204, 404):
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f"schema migration 2401, dropped smartstatus transform (status={response.status_code})"
                )
            else:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'schema migration 2401, unexpected status dropping smartstatus transform, status={response.status_code}, body="{response.text}"'
                )
        except Exception as e:
            get_effective_logger().warning(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2401, failed to drop smartstatus transform, exception="{str(e)}"'
            )
    else:
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f"schema migration 2401, smartstatus transform absent, nothing to drop"
        )

    # drop the collection — only if present
    if smartstatus_collection_exists:
        try:
            response = requests.post(
                f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvcollection',
                headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                data=json.dumps(
                    {"tenant_id": tenant_id, "collection_name": smartstatus_collection_name}
                ),
                verify=False,
                timeout=600,
            )
            if response.status_code in (200, 201, 202, 204, 404):
                get_effective_logger().info(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f"schema migration 2401, dropped smartstatus collection (status={response.status_code})"
                )
            else:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'schema migration 2401, unexpected status dropping smartstatus collection, status={response.status_code}, body="{response.text}"'
                )
        except Exception as e:
            get_effective_logger().warning(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2401, failed to drop smartstatus collection, exception="{str(e)}"'
            )
    else:
        get_effective_logger().debug(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f"schema migration 2401, smartstatus collection absent, nothing to drop"
        )

    # ─────────────────────────────────────────────────────────────────────
    # Concern C — variable-delay adaptive eligibility (DSM/DHM tenants).
    #
    # Historically, enabling variable delay forced allow_adaptive_delay="false"
    # ("mutual exclusion"): variable-delay entities were excluded from adaptive
    # delay. PR #1611 enhanced the adaptive framework to handle variable-delay
    # entities (the honour-existing-slots path), but the eligibility gate still
    # requires allow_adaptive_delay=="true" while the backend kept forcing it to
    # "false" — so the variable-delay adaptive path could never see a candidate.
    # 2.4.1 decouples the two (the forcing is removed at every write site).
    #
    # Backfill so existing variable-delay entities become eligible, but ONLY:
    #   - when the tenant has adaptive delay enabled (adaptive_delay==1); if the
    #     tenant has it disabled (incl. when the AI Feed Lifecycle Advisor owns
    #     DSM/DHM, which forces adaptive_delay=0), do nothing;
    #   - for entities using variable delay (variable_delay_policy=="variable");
    #   - that are not already opted in (allow_adaptive_delay != "true").
    # Static entities and already-true entities are left untouched. Idempotent.
    # Runs before the DHM-only Concern B return below so DSM-only tenants are
    # covered too.
    # ─────────────────────────────────────────────────────────────────────
    try:
        vtenant_account = trackme_vtenant_account_from_service(service, tenant_id)
        adaptive_delay_enabled = int(vtenant_account.get("adaptive_delay", 1))
    except Exception as e:
        adaptive_delay_enabled = 0
        get_effective_logger().warning(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'schema migration 2401 (Concern C), could not read adaptive_delay flag, '
            f'skipping variable-delay eligibility backfill, exception="{str(e)}"'
        )

    if adaptive_delay_enabled == 1:
        for vd_component in ("dsm", "dhm"):
            if vtenant_record.get(f"tenant_{vd_component}_enabled") != 1:
                continue
            vd_collection_name = f"kv_trackme_{vd_component}_tenant_{tenant_id}"
            try:
                vd_main_collection = service.kvstore[vd_collection_name]
            except Exception as e:
                get_effective_logger().warning(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'schema migration 2401 (Concern C), collection "{vd_collection_name}" not '
                    f'accessible, skipping, exception="{str(e)}"'
                )
                continue

            flipped = 0
            vd_end = False
            vd_skip = 0
            while not vd_end:
                try:
                    vd_batch = vd_main_collection.data.query(skip=vd_skip)
                except Exception as e:
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                        f'schema migration 2401 (Concern C), failed reading "{vd_collection_name}", '
                        f'exception="{str(e)}"'
                    )
                    break
                if not vd_batch:
                    vd_end = True
                    continue
                for vd_item in vd_batch:
                    if (
                        vd_item.get("variable_delay_policy") == "variable"
                        and vd_item.get("allow_adaptive_delay") != "true"
                    ):
                        vd_item["allow_adaptive_delay"] = "true"
                        try:
                            vd_main_collection.data.update(
                                str(vd_item.get("_key")), json.dumps(vd_item)
                            )
                            flipped += 1
                        except Exception as e:
                            get_effective_logger().warning(
                                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                                f'schema migration 2401 (Concern C), failed flipping allow_adaptive_delay '
                                f'on object_id="{vd_item.get("_key")}", exception="{str(e)}"'
                            )
                vd_skip += len(vd_batch)

            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'schema migration 2401 (Concern C), component="{vd_component}", set '
                f'allow_adaptive_delay="true" on {flipped} variable-delay entit(y/ies) '
                f"now eligible for adaptive delay"
            )
    else:
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f"schema migration 2401 (Concern C), adaptive_delay disabled for tenant, "
            f"no variable-delay eligibility backfill"
        )

    # ─────────────────────────────────────────────────────────────────────
    # Concern D — Delay/latency Threshold Intent Lock (DSM/DHM-enabled tenants).
    #   1. Create the per-tenant threshold-intent ledger collection + transform
    #      (kv_trackme_{component}_threshold_intent_tenant_<tid>) — the source of
    #      truth for operator-pinned delay/lag thresholds.
    #   2. Refresh the main DSM/DHM transform so the new
    #      data_max_delay_allowed_locked / data_max_lag_allowed_locked fields
    #      become visible to | lookup / | inputlookup on existing tenants.
    # Placed BEFORE Concern B's DHM-only early return below so DSM-only tenants
    # are provisioned too. Idempotent (delete-then-create transforms). New
    # tenants get all of this at creation via collections_list_{dsm,dhm}.
    # ─────────────────────────────────────────────────────────────────────
    ti_components = []
    if vtenant_record.get("tenant_dsm_enabled") == 1:
        ti_components.append("dsm")
    if vtenant_record.get("tenant_dhm_enabled") == 1:
        ti_components.append("dhm")

    if ti_components:
        ti_read_perms, ti_write_perms = get_permissions(vtenant_record)
        ti_default_sharing = (
            reqinfo.get("trackme_conf", {})
            .get("trackme_general", {})
            .get("trackme_default_sharing", "app")
        )
        ti_acl = {
            "owner": vtenant_record.get("tenant_owner"),
            "sharing": ti_default_sharing,
            "perms.write": ti_write_perms,
            "perms.read": ti_read_perms,
        }

        for ti_component in ti_components:

            # D.1 — create the threshold-intent ledger collection + transform
            ti_collection_name = (
                f"kv_trackme_{ti_component}_threshold_intent_tenant_{tenant_id}"
            )
            ti_transform_name = (
                f"trackme_{ti_component}_threshold_intent_tenant_{tenant_id}"
            )
            ti_transform_fields = collections_dict[
                f"trackme_{ti_component}_threshold_intent"
            ]

            try:
                response = requests.post(
                    f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection',
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(
                        {
                            "tenant_id": tenant_id,
                            "collection_name": ti_collection_name,
                            "collection_acl": ti_acl,
                            "owner": vtenant_record.get("tenant_owner"),
                        }
                    ),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", create threshold-intent KVstore collection failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", created threshold-intent collection="{ti_collection_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", failed to create threshold-intent collection="{ti_collection_name}", exception="{str(e)}"'
                )

            # Always (re)create the transform — decoupled from the collection
            # create response. A previous run may have created the collection but
            # failed before the transform, or create_kvcollection may report
            # non-2xx "already exists"; gating the transform on this-run success
            # would strand such tenants without the lookup transform. The create
            # endpoint is idempotent, so an unconditional attempt is safe and
            # keeps Concern D self-healing across retries.
            try:
                response = requests.post(
                    f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform',
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(
                        {
                            "tenant_id": tenant_id,
                            "transform_name": ti_transform_name,
                            "transform_fields": ti_transform_fields,
                            "collection_name": ti_collection_name,
                            "transform_acl": ti_acl,
                            "owner": vtenant_record.get("tenant_owner"),
                        }
                    ),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", create threshold-intent transform failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", created threshold-intent transform="{ti_transform_name}"'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", failed to create threshold-intent transform="{ti_transform_name}", exception="{str(e)}"'
                )

            # D.2 — refresh the main transform so the new *_locked fields are
            # exposed to | lookup. (For DHM this also happens in Concern B below
            # via the same collections_dict source; the redundant delete-create
            # is idempotent and keeps Concern D self-contained.)
            ti_main_transform = f"trackme_{ti_component}_tenant_{tenant_id}"
            ti_main_collection = f"kv_trackme_{ti_component}_tenant_{tenant_id}"
            ti_main_fields = collections_dict[f"trackme_{ti_component}"]
            try:
                requests.post(
                    f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform',
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(
                        {"tenant_id": tenant_id, "transform_name": ti_main_transform}
                    ),
                    verify=False,
                    timeout=600,
                )
                response = requests.post(
                    f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform',
                    headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
                    data=json.dumps(
                        {
                            "tenant_id": tenant_id,
                            "transform_name": ti_main_transform,
                            "transform_fields": ti_main_fields,
                            "collection_name": ti_main_collection,
                            "transform_acl": ti_acl,
                            "owner": vtenant_record.get("tenant_owner"),
                        }
                    ),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 202, 204):
                    get_effective_logger().error(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", refresh main transform failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", refreshed main transform="{ti_main_transform}" for threshold-lock fields'
                    )
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401 (Concern D), tenant_id="{tenant_id}", component="{ti_component}", failed to refresh main transform="{ti_main_transform}", exception="{str(e)}"'
                )

    # ─────────────────────────────────────────────────────────────────────
    # Concern B — introduce the DHM `asset` field (DHM-enabled tenants only).
    # ─────────────────────────────────────────────────────────────────────
    if vtenant_record.get("tenant_dhm_enabled") != 1:
        get_effective_logger().info(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f"DHM not enabled, skipping DHM asset step; schema migration 2401 terminated"
        )
        return True

    # ─────────────────────────────────────────────────────────────────────
    # B.1: refresh the central DHM lookup transform so its fields_list picks up
    # the new `asset` field for existing tenants (delete-then-create via the
    # admin REST endpoints, mirroring migration 2316).
    # ─────────────────────────────────────────────────────────────────────
    transform_name = f"trackme_dhm_tenant_{tenant_id}"
    central_collection_name = f"kv_trackme_dhm_tenant_{tenant_id}"
    transform_fields = collections_dict["trackme_dhm"]

    tenant_roles_read_perms, tenant_roles_write_perms = get_permissions(vtenant_record)
    definition_acl = {
        "owner": vtenant_record.get("tenant_owner"),
        "sharing": "app",
        "perms.write": tenant_roles_write_perms,
        "perms.read": tenant_roles_read_perms,
    }

    # delete the existing transform
    try:
        response = requests.post(
            f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform',
            headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
            data=json.dumps(
                {"tenant_id": tenant_id, "transform_name": transform_name}
            ),
            verify=False,
            timeout=600,
        )
        if response.status_code not in (200, 201, 202, 204):
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
                f'failed to delete central DHM transform, response.status_code="{response.status_code}", response.text="{response.text}"'
            )
        else:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
                f'successfully deleted central DHM transform, transform="{transform_name}"'
            )
    except Exception as e:
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
            f'failed to delete central DHM transform, transform="{transform_name}", exception="{str(e)}"'
        )

    # recreate the transform with the latest field definitions (now incl. asset)
    try:
        response = requests.post(
            f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform',
            headers={"Authorization": f'Splunk {reqinfo["session_key"]}'},
            data=json.dumps(
                {
                    "tenant_id": tenant_id,
                    "transform_name": transform_name,
                    "transform_fields": transform_fields,
                    "collection_name": central_collection_name,
                    "transform_acl": definition_acl,
                    "owner": vtenant_record.get("tenant_owner"),
                }
            ),
            verify=False,
            timeout=600,
        )
        if response.status_code not in (200, 201, 202, 204):
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
                f'failed to create central DHM transform, response.status_code="{response.status_code}", response.text="{response.text}"'
            )
        else:
            get_effective_logger().info(
                f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
                f'successfully recreated central DHM transform, transform="{transform_name}"'
            )
    except Exception as e:
        get_effective_logger().error(
            f'task="{task_name}", task_instance_id={task_instance_id}, schema migration 2401, tenant_id="{tenant_id}", '
            f'failed to create central DHM transform, transform="{transform_name}", exception="{str(e)}"'
        )

    # ─────────────────────────────────────────────────────────────────────
    # B.2: backfill the `asset` field on existing entity records.
    # ─────────────────────────────────────────────────────────────────────
    collection_name = f"kv_trackme_dhm_tenant_{tenant_id}"
    try:
        collection = service.kvstore[collection_name]
        existing_records, existing_keys, existing_dict = get_kv_collection(
            collection, collection_name
        )
    except Exception as e:
        get_effective_logger().warning(
            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
            f'non-fatal: could not load collection="{collection_name}", exception="{str(e)}"'
        )
        return True

    records_to_update = []
    records_updated_count = 0
    records_skipped_count = 0
    records_error_count = 0

    for record in existing_records:
        try:
            new_asset = build_dhm_asset_list(
                record.get("object"), record.get("alias")
            )
            # nothing computable (no usable object/alias) — leave the record as is
            if not new_asset:
                records_skipped_count += 1
                continue

            # normalise the currently-stored value for an idempotent comparison
            current_asset = record.get("asset")
            if isinstance(current_asset, list):
                current_norm = sorted(str(v).lower() for v in current_asset if v)
            elif current_asset:
                current_norm = [str(current_asset).lower()]
            else:
                current_norm = []

            if current_norm == new_asset:
                records_skipped_count += 1
                continue

            record["asset"] = new_asset
            records_to_update.append(record)
            records_updated_count += 1

        except Exception as e_record:
            records_error_count += 1
            get_effective_logger().error(
                f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                f'error computing asset for record _key="{record.get("_key", "unknown")}", exception="{str(e_record)}"'
            )
            continue

    if records_to_update:
        chunk_size = 500
        for i in range(0, len(records_to_update), chunk_size):
            chunk = records_to_update[i : i + chunk_size]
            try:
                collection.data.batch_save(*chunk)
            except Exception as e:
                get_effective_logger().error(
                    f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                    f'batch_save failed for chunk starting at {i}, falling back to per-record update, exception="{str(e)}"'
                )
                for record in chunk:
                    try:
                        collection.data.update(
                            record.get("_key"), json.dumps(record)
                        )
                    except Exception as e2:
                        records_error_count += 1
                        get_effective_logger().error(
                            f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
                            f'failed to update record _key="{record.get("_key")}", exception="{str(e2)}"'
                        )

    get_effective_logger().info(
        f'task="{task_name}", task_instance_id={task_instance_id}, tenant_id="{tenant_id}", '
        f"schema migration 2401 terminated (smartstatus decommissioned, DHM transform refreshed, asset backfilled), "
        f"records_updated={records_updated_count}, records_skipped={records_skipped_count}, records_error={records_error_count}"
    )
    return True

