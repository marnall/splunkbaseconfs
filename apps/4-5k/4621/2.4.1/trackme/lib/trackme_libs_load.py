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
import logging

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
from trackme_libs_logging import get_effective_logger

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def get_suffix(s):
    parts = s.split("-")
    return parts[-1]


def getfieldvalue(jsonData, fieldName):
    value = jsonData.get(fieldName, "null")
    if isinstance(value, bool):
        # Preserve numerical boolean values
        return int(value)
    return value


def _parse_csv_or_list(value):
    """Return a set from either a list or a comma-separated string. Empty / None → empty set."""
    if not value:
        return set()
    if isinstance(value, list):
        return {str(v).strip() for v in value if str(v).strip()}
    return {tok.strip() for tok in str(value).split(",") if tok.strip()}


def has_user_access(effective_roles, record, username=None):
    tenant_roles_admin = (
        set(record["tenant_roles_admin"])
        if isinstance(record["tenant_roles_admin"], list)
        else set(record["tenant_roles_admin"].split(","))
    )
    tenant_roles_power = (
        set(record["tenant_roles_power"])
        if isinstance(record["tenant_roles_power"], list)
        else set(record["tenant_roles_power"].split(","))
    )
    tenant_roles_user = (
        set(record["tenant_roles_user"])
        if isinstance(record["tenant_roles_user"], list)
        else set(record["tenant_roles_user"].split(","))
    )
    allowed_roles = (
        tenant_roles_admin
        | tenant_roles_user
        | tenant_roles_power
        | {"admin", "trackme_admin", "sc_admin"}
    )

    role_match = bool(set(effective_roles) & allowed_roles)
    if not role_match:
        return False

    # Optional per-tenant username allowlist (vtenant_account.tenant_allowed_users)
    # carried onto the record by the caller. Empty/missing → no username restriction.
    # When set: only listed users (plus the tenant_owner) pass the additional gate.
    # splunk-system-user is handled by callers via a short-circuit before this fn.
    allowed_users = _parse_csv_or_list(record.get("tenant_allowed_users"))
    if not allowed_users:
        return True

    if username and username in allowed_users:
        return True

    tenant_owner = record.get("tenant_owner") or ""
    if username and tenant_owner and username == tenant_owner:
        return True

    return False


def get_effective_roles(user_roles, roles_dict):
    effective_roles = set(user_roles)  # start with user's direct roles
    to_check = list(user_roles)  # roles to be checked for inherited roles

    while to_check:
        current_role = to_check.pop()
        inherited_roles = roles_dict.get(current_role, [])
        for inherited_role in inherited_roles:
            if inherited_role not in effective_roles:
                effective_roles.add(inherited_role)
                to_check.append(inherited_role)

    return effective_roles


def resolve_effective_roles_for_user(service, username):
    """Return the set of effective Splunk roles for *username*, or None for
    the internal splunk-system-user (which bypasses RBAC).
    Centralises the service.users / service.roles iteration so callers
    don't duplicate this pattern."""
    if username == "splunk-system-user":
        return None
    username_roles = []
    for user in service.users:
        if user.name == username:
            username_roles = user.roles
            break
    roles_dict = {}
    for role in service.roles:
        imported_roles_value = role.content.get("imported_roles", [])
        if imported_roles_value:
            roles_dict[role.name] = imported_roles_value
    return get_effective_roles(username_roles, roles_dict)


def process_exec_summary(exec_summary_json):
    try:
        summary_data = json.loads(exec_summary_json)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input")

    components_data = {}
    for item in summary_data.values():
        component = item["component"]

        if component not in components_data:
            components_data[component] = {"last_exec": 0.0, "status": 0}

        # get last_exec
        try:
            last_exec = float(item["last_exec"])
        except Exception as e:
            last_exec = 0.0

        if last_exec > components_data[component]["last_exec"]:
            components_data[component]["last_exec"] = last_exec

        if item["last_status"] == "failure":
            components_data[component]["status"] = 1

    return components_data


def get_vtenants_accounts(session_key, splunkd_uri):
    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # Add the vtenant account
    url = "%s/services/trackme/v2/vtenants/vtenants_accounts" % (splunkd_uri)

    # Proceed
    try:
        response = requests.post(url, headers=header, verify=False, timeout=600)
        if response.status_code not in (200, 201, 204):
            msg = f'get vtenant account has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
            raise Exception(msg)
        else:
            vtenants_account = response.json()
            get_effective_logger().debug(
                f'get vtenant account was operated successfully, response.status_code="{response.status_code}"'
            )
            get_effective_logger().debug(f"vtenants_account={json.dumps(vtenants_account, indent=2)}")
    except Exception as e:
        msg = f'get vtenant account has failed, exception="{str(e)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    return vtenants_account


def trackmeload(session_key, splunkd_uri, service, users, roles, username, mode):
    # Get roles for the current user
    username_roles = []
    for user in users:
        if user.name == username:
            username_roles = user.roles
    get_effective_logger().info(f'username="{username}", roles="{username_roles}"')

    # get roles
    roles_dict = {}

    for role in roles:
        imported_roles_value = role.content.get("imported_roles", [])
        if imported_roles_value:  # Check if it has a non-empty value
            roles_dict[role.name] = imported_roles_value

    get_effective_logger().debug(f"roles_dict={json.dumps(roles_dict, indent=2)}")

    # get effective roles, which takes into account both direct membership and inheritance
    effective_roles = get_effective_roles(username_roles, roles_dict)

    # Data collection
    collection_name = "kv_trackme_virtual_tenants"
    collection = service.kvstore[collection_name]

    # Summary state collection
    summary_state_collection_name = "kv_trackme_virtual_tenants_entities_summary"
    summary_state_collection = service.kvstore[summary_state_collection_name]

    # Exec summary collection
    exec_summary_collection_name = "kv_trackme_virtual_tenants_exec_summary"
    exec_summary_collection = service.kvstore[exec_summary_collection_name]

    # get vtenants_account
    try:
        vtenants_account = get_vtenants_accounts(
            session_key,
            splunkd_uri,
        )
    except Exception as e:
        raise Exception(f'get_vtenants_accounts has failed with exception="{str(e)}"')

    # final yield record
    yield_record = []

    # faulty tenants: tenants that exist in KV store but have missing/corrupted vtenant_account
    faulty_tenants = []

    # Get the records
    filtered_records = []
    try:
        records = collection.data.query()

        # loop through records, for each record get the alias value from vtenants_account
        # and  add to the record
        valid_records = []
        for record in records:
            # get the tenant_id
            tenant_id = record["tenant_id"]

            # get the alias - skip tenant if vtenant_account is missing
            if tenant_id not in vtenants_account:
                get_effective_logger().warning(
                    f'tenant_id="{tenant_id}" exists in KV store but has no vtenant_account configuration, '
                    f"skipping this tenant — auto-recovery will be attempted after loading completes"
                )
                faulty_tenants.append({"tenant_id": tenant_id})
                continue

            alias = vtenants_account[tenant_id].get("alias", tenant_id)

            # add alias to record
            record["tenant_alias"] = alias

            # Per-tenant username allowlist (vtenant_account-level config). Empty
            # = no restriction. Carried onto the record so has_user_access() can
            # apply it without re-fetching vtenants_account.
            record["tenant_allowed_users"] = vtenants_account[tenant_id].get(
                "tenant_allowed_users", ""
            )
            valid_records.append(record)

        sorted_records = sorted(valid_records, key=lambda x: x["tenant_alias"])

        # Filter records based on user access
        filtered_records = [
            record
            for record in sorted_records
            if has_user_access(effective_roles, record, username)
            or username in ("splunk-system-user")
        ]

        # render
        for filtered_record in filtered_records:
            try:
                # log debug
                get_effective_logger().debug(
                    f'Inspecting record="{json.dumps(filtered_record, indent=2)}"'
                )

                # get the tenant_id
                tenant_id = filtered_record["tenant_id"]

                # lookup the summary state
                try:
                    query_string = {
                        "tenant_id": tenant_id,
                    }
                    summary_state_record = summary_state_collection.data.query(
                        query=json.dumps(query_string)
                    )[0]
                    get_effective_logger().debug(
                        f'tenant_id="{tenant_id}", summary state found, record="{json.dumps(summary_state_record)}"'
                    )

                    # add summary_state_record fields to filtered_record
                    for k, v in summary_state_record.items():
                        if k != "tenant_id" and not k.startswith("_"):
                            filtered_record[k] = v

                except Exception as e:
                    get_effective_logger().debug(
                        f'tenant_id="{tenant_id}", no summary state is available, exception="{str(e)}"'
                    )

                # Read and process tenant_objects_exec_summary from the dedicated collection
                try:
                    exec_summary_query = {"tenant_id": tenant_id}
                    exec_summary_records = exec_summary_collection.data.query(
                        query=json.dumps(exec_summary_query)
                    )
                    if exec_summary_records:
                        exec_summary_raw = exec_summary_records[0].get("tenant_objects_exec_summary")
                        filtered_record["tenant_objects_exec_summary"] = exec_summary_raw
                        exec_summary_data = process_exec_summary(exec_summary_raw)
                        for component, data in exec_summary_data.items():
                            # get suffix
                            short_component = get_suffix(component)

                            filtered_record[f"{short_component}_status"] = data[
                                "status"
                            ]
                            filtered_record[f"{short_component}_last_exec"] = data[
                                "last_exec"
                            ]
                except Exception as e:
                    get_effective_logger().error(
                        f'tenant_id="{tenant_id}", failed to process exec summary, exception="{str(e)}"'
                    )

                # yield needs to be explicit and gen field names and values explicitly
                try:
                    tenant_id = getfieldvalue(filtered_record, "tenant_id")
                    description = vtenants_account[tenant_id].get("description", "")
                    alias = vtenants_account[tenant_id].get("alias", tenant_id)

                    new_record = {
                        "tenant_id": tenant_id,
                        "tenant_alias": alias,
                        "tenant_status": getfieldvalue(
                            filtered_record, "tenant_status"
                        ),
                        "tenant_desc": description,
                        "tenant_owner": getfieldvalue(filtered_record, "tenant_owner"),
                        "tenant_roles_admin": getfieldvalue(
                            filtered_record, "tenant_roles_admin"
                        ),
                        "tenant_roles_user": getfieldvalue(
                            filtered_record, "tenant_roles_user"
                        ),
                        "tenant_dsm_enabled": getfieldvalue(
                            filtered_record, "tenant_dsm_enabled"
                        ),
                        "tenant_cim_enabled": getfieldvalue(
                            filtered_record, "tenant_cim_enabled"
                        ),
                        "tenant_flx_enabled": getfieldvalue(
                            filtered_record, "tenant_flx_enabled"
                        ),
                        "tenant_fqm_enabled": getfieldvalue(
                            filtered_record, "tenant_fqm_enabled"
                        ),
                        "tenant_dhm_enabled": getfieldvalue(
                            filtered_record, "tenant_dhm_enabled"
                        ),
                        "tenant_mhm_enabled": getfieldvalue(
                            filtered_record, "tenant_mhm_enabled"
                        ),
                        "tenant_wlk_enabled": getfieldvalue(
                            filtered_record, "tenant_wlk_enabled"
                        ),
                        # ML Outliers gate — the Manage AI Agents automation page reads
                        # both to determine whether the automated ML
                        # Inspector can run on this tenant (master switch
                        # AND at least one enabled component in the
                        # allowlist).
                        "tenant_mloutliers": getfieldvalue(
                            filtered_record, "tenant_mloutliers"
                        ),
                        "tenant_mloutliers_allowlist": getfieldvalue(
                            filtered_record, "tenant_mloutliers_allowlist"
                        ),
                        "tenant_dhm_root_constraint": getfieldvalue(
                            filtered_record, "tenant_dhm_root_constraint"
                        ),
                        "tenant_mhm_root_constraint": getfieldvalue(
                            filtered_record, "tenant_mhm_root_constraint"
                        ),
                        "tenant_cim_objects": getfieldvalue(
                            filtered_record, "tenant_cim_objects"
                        ),
                        "tenant_alert_objects": getfieldvalue(
                            filtered_record, "tenant_alert_objects"
                        ),
                        "tenant_dsm_hybrid_objects": getfieldvalue(
                            filtered_record, "tenant_dsm_hybrid_objects"
                        ),
                        "tenant_objects_exec_summary": getfieldvalue(
                            filtered_record, "tenant_objects_exec_summary"
                        ),
                        "tenant_idx_settings": getfieldvalue(
                            filtered_record, "tenant_idx_settings"
                        ),
                        "tenant_replica": getfieldvalue(
                            filtered_record, "tenant_replica"
                        ),
                        "key": getfieldvalue(filtered_record, "_key"),
                        "report_entities_count": getfieldvalue(
                            filtered_record, "report_entities_count"
                        ),
                        "dhm_entities": getfieldvalue(filtered_record, "dhm_entities"),
                        "dhm_critical_red_priority": getfieldvalue(
                            filtered_record, "dhm_critical_red_priority"
                        ),
                        "dhm_high_red_priority": getfieldvalue(
                            filtered_record, "dhm_high_red_priority"
                        ),
                        "dhm_last_exec": getfieldvalue(
                            filtered_record, "dhm_last_exec"
                        ),
                        "dhm_low_red_priority": getfieldvalue(
                            filtered_record, "dhm_low_red_priority"
                        ),
                        "dhm_medium_red_priority": getfieldvalue(
                            filtered_record, "dhm_medium_red_priority"
                        ),
                        "dsm_entities": getfieldvalue(filtered_record, "dsm_entities"),
                        "dsm_critical_red_priority": getfieldvalue(
                            filtered_record, "dsm_critical_red_priority"
                        ),
                        "dsm_high_red_priority": getfieldvalue(
                            filtered_record, "dsm_high_red_priority"
                        ),
                        "dsm_last_exec": getfieldvalue(
                            filtered_record, "dsm_last_exec"
                        ),
                        "dsm_low_red_priority": getfieldvalue(
                            filtered_record, "dsm_low_red_priority"
                        ),
                        "dsm_medium_red_priority": getfieldvalue(
                            filtered_record, "dsm_medium_red_priority"
                        ),
                        "mhm_entities": getfieldvalue(filtered_record, "mhm_entities"),
                        "mhm_critical_red_priority": getfieldvalue(
                            filtered_record, "mhm_critical_red_priority"
                        ),
                        "mhm_high_red_priority": getfieldvalue(
                            filtered_record, "mhm_high_red_priority"
                        ),
                        "mhm_last_exec": getfieldvalue(
                            filtered_record, "mhm_last_exec"
                        ),
                        "mhm_low_red_priority": getfieldvalue(
                            filtered_record, "mhm_low_red_priority"
                        ),
                        "mhm_medium_red_priority": getfieldvalue(
                            filtered_record, "mhm_medium_red_priority"
                        ),
                        "cim_entities": getfieldvalue(filtered_record, "cim_entities"),
                        "cim_critical_red_priority": getfieldvalue(
                            filtered_record, "cim_critical_red_priority"
                        ),
                        "cim_high_red_priority": getfieldvalue(
                            filtered_record, "cim_high_red_priority"
                        ),
                        "cim_last_exec": getfieldvalue(
                            filtered_record, "cim_last_exec"
                        ),
                        "cim_low_red_priority": getfieldvalue(
                            filtered_record, "cim_low_red_priority"
                        ),
                        "cim_medium_red_priority": getfieldvalue(
                            filtered_record, "cim_medium_red_priority"
                        ),
                        "flx_entities": getfieldvalue(filtered_record, "flx_entities"),
                        "flx_critical_red_priority": getfieldvalue(
                            filtered_record, "flx_critical_red_priority"
                        ),
                        "flx_high_red_priority": getfieldvalue(
                            filtered_record, "flx_high_red_priority"
                        ),
                        "flx_last_exec": getfieldvalue(
                            filtered_record, "flx_last_exec"
                        ),
                        "flx_low_red_priority": getfieldvalue(
                            filtered_record, "flx_low_red_priority"
                        ),
                        "flx_medium_red_priority": getfieldvalue(
                            filtered_record, "flx_medium_red_priority"
                        ),
                        "fqm_entities": getfieldvalue(filtered_record, "fqm_entities"),
                        "fqm_critical_red_priority": getfieldvalue(
                            filtered_record, "fqm_critical_red_priority"
                        ),
                        "fqm_high_red_priority": getfieldvalue(
                            filtered_record, "fqm_high_red_priority"
                        ),
                        "fqm_last_exec": getfieldvalue(
                            filtered_record, "fqm_last_exec"
                        ),
                        "fqm_low_red_priority": getfieldvalue(
                            filtered_record, "fqm_low_red_priority"
                        ),
                        "fqm_medium_red_priority": getfieldvalue(
                            filtered_record, "fqm_medium_red_priority"
                        ),
                        "wlk_entities": getfieldvalue(filtered_record, "wlk_entities"),
                        "wlk_critical_red_priority": getfieldvalue(
                            filtered_record, "wlk_critical_red_priority"
                        ),
                        "wlk_high_red_priority": getfieldvalue(
                            filtered_record, "wlk_high_red_priority"
                        ),
                        "wlk_last_exec": getfieldvalue(
                            filtered_record, "wlk_last_exec"
                        ),
                        "wlk_low_red_priority": getfieldvalue(
                            filtered_record, "wlk_low_red_priority"
                        ),
                        "wlk_medium_red_priority": getfieldvalue(
                            filtered_record, "wlk_medium_red_priority"
                        ),
                        "all_status": getfieldvalue(filtered_record, "all_status"),
                        "dhm_status": getfieldvalue(filtered_record, "dhm_status"),
                        "dsm_status": getfieldvalue(filtered_record, "dsm_status"),
                        "mhm_status": getfieldvalue(filtered_record, "mhm_status"),
                        "cim_status": getfieldvalue(filtered_record, "cim_status"),
                        "flx_status": getfieldvalue(filtered_record, "flx_status"),
                        "fqm_status": getfieldvalue(filtered_record, "fqm_status"),
                        "wlk_status": getfieldvalue(filtered_record, "wlk_status"),
                        "all_last_exec": getfieldvalue(
                            filtered_record, "all_last_exec"
                        ),
                        "dhm_last_exec": getfieldvalue(
                            filtered_record, "dhm_last_exec"
                        ),
                        "dsm_last_exec": getfieldvalue(
                            filtered_record, "dsm_last_exec"
                        ),
                        "mhm_last_exec": getfieldvalue(
                            filtered_record, "mhm_last_exec"
                        ),
                        "cim_last_exec": getfieldvalue(
                            filtered_record, "cim_last_exec"
                        ),
                        "flx_last_exec": getfieldvalue(
                            filtered_record, "flx_last_exec"
                        ),
                        "fqm_last_exec": getfieldvalue(
                            filtered_record, "fqm_last_exec"
                        ),
                        "wlk_last_exec": getfieldvalue(
                            filtered_record, "wlk_last_exec"
                        ),
                    }

                    yield_record.append(new_record)
                except Exception as e:
                    get_effective_logger().error(
                        f'Failed to process tenant "{tenant_id}", skipping record, this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception: {str(e)}'
                    )
                    continue
            except Exception as e:
                get_effective_logger().error(
                    f"Failed to process tenant record, skipping. Exception: {str(e)}"
                )
                continue

    except Exception as e:
        raise Exception(
            f'Failed to retrieve tenants, this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception="{str(e)}"'
        )

    # return
    result = {
        "tenants": yield_record,
    }

    # include faulty tenants if any were detected, and attempt auto-recovery outside the main loop
    if faulty_tenants:
        result["faulty_tenants"] = faulty_tenants

        # Attempt auto-recovery for all faulty tenants after the main processing is complete
        # This avoids blocking the per-record loop with sequential HTTP calls
        maintain_url = (
            "%s/services/trackme/v2/configuration/admin/maintain_vtenant_account"
            % (splunkd_uri)
        )
        maintain_header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }
        for faulty in faulty_tenants:
            faulty_tid = faulty["tenant_id"]
            try:
                maintain_response = requests.post(
                    maintain_url,
                    headers=maintain_header,
                    data=json.dumps(
                        {
                            "tenant_id": faulty_tid,
                            "force_create_missing": "true",
                        }
                    ),
                    verify=False,
                    timeout=30,
                )
                if maintain_response.status_code in (200, 201, 204):
                    get_effective_logger().info(
                        f'auto-recovery for tenant_id="{faulty_tid}" was successful, '
                        f"the tenant account has been recreated with defaults"
                    )
                else:
                    get_effective_logger().error(
                        f'auto-recovery for tenant_id="{faulty_tid}" failed, '
                        f"status_code={maintain_response.status_code}, response={maintain_response.text}"
                    )
            except Exception as maintain_e:
                get_effective_logger().error(
                    f'auto-recovery for tenant_id="{faulty_tid}" failed with exception="{str(maintain_e)}"'
                )

    if mode == "full":
        return result

    elif mode == "expanded":
        yield_response = []
        for tenant_record in yield_record:
            yield_response.append(tenant_record)
        result["tenants"] = yield_response
        return result


def load_group_shared_data(service, logger=None):
    """
    Load the two KV Store collections shared by all virtual-group summary computations.
    Call this once and pass the result to compute_group_component_summary to avoid
    redundant full-collection loads when processing multiple groups.

    Returns:
        tuple (tenant_lookup, summary_by_tenant)
            tenant_lookup:      dict keyed by tenant_id → tenant record
            summary_by_tenant:  dict keyed by tenant_id → summary record
    """
    try:
        tenant_records = service.kvstore["kv_trackme_virtual_tenants"].data.query()
    except Exception as e:
        if logger:
            logger.error(f'load_group_shared_data step="load_tenants" exception="{str(e)}"')
        tenant_records = []

    tenant_lookup = {}
    for tr in tenant_records:
        tid = tr.get("tenant_id")
        if tid:
            tenant_lookup[tid] = tr

    try:
        summary_records = service.kvstore["kv_trackme_virtual_tenants_entities_summary"].data.query()
    except Exception as e:
        if logger:
            logger.error(f'load_group_shared_data step="load_summary" exception="{str(e)}"')
        summary_records = []

    summary_by_tenant = {}
    for sr in summary_records:
        tid = sr.get("tenant_id")
        if tid:
            summary_by_tenant[tid] = sr

    return tenant_lookup, summary_by_tenant


def compute_group_component_summary(service, tenants_scope, vtenants_account, logger=None,
                                    tenant_lookup=None, summary_by_tenant=None):
    """
    Shared aggregation pipeline used by both post_load_group_summary (user handler)
    and post_simulate_group (admin handler).

    Loads kv_trackme_virtual_tenants + kv_trackme_virtual_tenants_entities_summary
    and computes per-component counts for the provided tenants_scope.

    Args:
        service:            splunklib.client.Service (already connected)
        tenants_scope:      list of {"tenant_id": str, "components": [str, ...]}
        vtenants_account:   dict keyed by tenant_id with {"alias": str} (from get_vtenants_accounts)
        logger:             optional logger for error reporting
        tenant_lookup:      pre-loaded tenant dict (from load_group_shared_data); loaded if None
        summary_by_tenant:  pre-loaded summary dict (from load_group_shared_data); loaded if None

    Returns:
        tuple (component_summary, components_sorted, tenant_details)
    """

    def safe_int(val):
        try:
            return int(val) if val is not None else 0
        except (ValueError, TypeError):
            return 0

    # Load collections only when not pre-supplied by a batch caller
    if tenant_lookup is None or summary_by_tenant is None:
        tenant_lookup, summary_by_tenant = load_group_shared_data(service, logger=logger)

    # Aggregate
    component_summary = {}
    tenant_details = []
    components_all = set()

    for scope_entry in tenants_scope:
        tenant_id = scope_entry.get("tenant_id", "")
        components = scope_entry.get("components", [])

        if tenant_id not in tenant_lookup:
            continue

        tenant_record = tenant_lookup[tenant_id]
        tenant_status = str(tenant_record.get("tenant_status", "")).lower()
        if tenant_status != "enabled":
            continue

        summary = summary_by_tenant.get(tenant_id, {})
        tenant_alias = vtenants_account.get(tenant_id, {}).get("alias", tenant_id)

        enabled_components = []
        for comp in components:
            # tenant_{comp}_enabled is stored as a Python bool in KV Store
            # (field.tenant_dsm_enabled = bool in collections.conf). str() of
            # True is "True", not "1", so a truthy check is required.
            if not tenant_record.get(f"tenant_{comp}_enabled", False):
                continue

            enabled_components.append(comp)
            components_all.add(comp)

            if comp not in component_summary:
                component_summary[comp] = {
                    "total": 0,
                    "green": 0,
                    "red": 0,
                    "orange": 0,
                    "blue": 0,
                    "critical_priority": 0,
                    "high_priority": 0,
                    "medium_priority": 0,
                    "low_priority": 0,
                }

            # Note: {comp}_entities counts ALL entities regardless of monitored_state.
            # total is recomputed below as green+orange+blue+red (enabled-only counts)
            # after all state accumulation is done, to match enrichGroupWithEntityFilter.

            for priority in ("critical", "high", "medium", "low"):
                count = safe_int(summary.get(f"{comp}_{priority}_red_priority"))
                component_summary[comp]["red"] += count
                component_summary[comp][f"{priority}_priority"] += count

            # Parse extended_stats JSON blob for green/orange/blue counts
            try:
                extended_raw = summary.get(f"{comp}_extended_stats", "{}")
                if isinstance(extended_raw, str):
                    extended = json.loads(extended_raw)
                elif isinstance(extended_raw, dict):
                    extended = extended_raw
                else:
                    extended = {}
                component_summary[comp]["green"] += safe_int(extended.get("count_green_enabled"))
                component_summary[comp]["orange"] += safe_int(extended.get("count_orange_enabled"))
                component_summary[comp]["blue"] += safe_int(extended.get("count_blue_enabled"))
            except (ValueError, TypeError, AttributeError):
                pass

        # Only list tenants that contribute at least one enabled component
        if enabled_components:
            tenant_details.append({
                "tenant_id": tenant_id,
                "tenant_alias": tenant_alias,
                "tenant_status": tenant_status,
                "components": enabled_components,
            })

    # Recompute total as sum of enabled-state counts (green + orange + blue + red).
    # green/orange/blue come from count_{state}_enabled in extended_stats; red comes
    # from {comp}_{priority}_red_priority — all enabled-only fields.
    # This matches enrichGroupWithEntityFilter (client path) which filters to
    # monitored_state='enabled' before counting, so both paths are now consistent.
    for comp_counts in component_summary.values():
        comp_counts["total"] = (
            comp_counts["green"] + comp_counts["orange"] +
            comp_counts["blue"] + comp_counts["red"]
        )

    return component_summary, sorted(list(components_all)), tenant_details
