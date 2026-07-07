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
import time
import logging
import json
import threading

# Networking and URL handling imports
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    trackme_audit_event,
    trackme_vtenant_account_from_service,
)

# import trackme libs get data
from trackme_libs_get_data import (
    batch_find_records_by_object,
    batch_find_records_by_key,
)

# import splunklib
from splunklib import client

# import trackme libs audit
from trackme_libs_audit import verify_type_values, trackme_audits_callback

# import shadow copy libs
from trackme_libs_shadow import patch_shadow_records, patch_shadow_records_full

"""
This function performs a bulk edit on given JSON data.
It generalizes the operation for various components.
:param request_info: Contains request related information
:param component_name: Name of the component (e.g., dsm, dhm, mhm)
:param persistent_fields: List of persistent fields specific to the component
:param collection_name_suffix: Suffix to construct the collection name
:param endpoint_suffix: Suffix for the URL prefix in resource_spl_example
    (e.g. "dsm" produces "/services/trackme/v2/splk_dsm/write/...")
:param function_name: Actual handler function name for the resource_spl_example
    URL (e.g. "ds_bulk_edit"). When omitted, falls back to
    f"{endpoint_suffix}_bulk_edit" — but DSM/DHM/MHM use a shorter ds_/dh_/mh_
    prefix on the function name, so callers MUST supply this for those
    components or the SPL example will produce a 404.
:param kwargs: Other keyword arguments
:return: Status and payload of the bulk edit operation
"""


def post_bulk_edit(
    self,
    log=None,
    loglevel=None,
    service=None,
    request_info=None,
    component_name=None,
    persistent_fields=None,
    collection_name_suffix=None,
    endpoint_suffix=None,
    function_name=None,
    **kwargs,
):
    # perf counter
    start_time = time.time()

    # Retrieve from data
    try:
        resp_dict = json.loads(str(request_info.raw_args["payload"]))
    except Exception as e:
        resp_dict = None

    if resp_dict is not None:
        try:
            describe = resp_dict["describe"]
            describe = describe.lower() == "true"
        except Exception:
            describe = False
        if not describe:
            tenant_id = resp_dict["tenant_id"]
            json_data = resp_dict["json_data"]
            # if not a dict or a list, load using json.loads
            if not isinstance(json_data, (dict, list)):
                json_data = json.loads(json_data)
    else:
        # body is required in this endpoint, if not submitted describe the usage
        describe = True

    if describe:
        # Resolve the handler function name for the SPL example URL. Callers
        # supply ``function_name`` explicitly because DSM/DHM/MHM functions
        # are named ``ds_/dh_/mh_bulk_edit`` (no trailing ``m``) while the
        # ``endpoint_suffix`` URL component keeps the full ``dsm/dhm/mhm``
        # prefix. Falling back blindly to ``{endpoint_suffix}_bulk_edit``
        # produces a 404 on copy-paste for those three components.
        spl_function_name = function_name or f"{endpoint_suffix}_bulk_edit"
        response = {
            "describe": (
                "This endpoint performs a bulk edit on one or more entities "
                "in the given component. It accepts an array of partial "
                "records — each entry MUST include a 'keyid' (the entity's "
                "KV record _key, used for lookup) and one or more updatable "
                "fields. Only fields in the component's persistent_fields "
                "allowlist are applied; unknown fields are silently ignored. "
                "Changes are recorded per-entity in the audit log. For DSM "
                "and DHM, setting variable_delay_policy automatically "
                "enforces the related data_override_lagging_class default. "
                "allow_adaptive_delay is intentionally independent (a "
                "per-entity opt-in, default 'true') and changes only when "
                "explicitly provided in the payload."
            ),
            "resource_desc": "Bulk-update a list of entities in one call (per-field updates with audit trail)",
            "resource_spl_example": f'| trackme url="/services/trackme/v2/splk_{endpoint_suffix}/write/{spl_function_name}" '
            + "mode=\"post\" body=\"{'tenant_id':'mytenant', "
            + "'json_data':[{'keyid':'b55658d1fc032ea3e1ecfc9eb60ad070','object':'netscreen:netscreen:firewall',"
            + "'alias':'netscreen:netscreen:firewall','priority':'high','monitored_state':'enabled',"
            + "'data_override_lagging_class':'false','data_max_lag_allowed':'3600',"
            + "'data_max_delay_allowed':'3600'}]}\"",
            "options": [
                {
                    "tenant_id": "REQUIRED. The tenant identifier",
                    "json_data": "REQUIRED. JSON array of partial records to apply. Each entry MUST contain 'keyid' (the entity's KV _key) and one or more updatable fields drawn from the component's persistent_fields allowlist. Records whose keyid does not match an existing entity are silently skipped",
                    "update_comment": "OPTIONAL. Comment recorded in the audit log for each entity changed. Defaults to 'API update' when omitted",
                }
            ],
        }
        return response, 200

    # Update comment is optional and used for audit changes
    update_comment = resp_dict.get("update_comment", "API update")
    # normalise if necessary
    if update_comment == "N/A":
        update_comment = "No comment for update."

    # counters
    failures_count = 0

    # Data collection
    collection_name = f"kv_trackme_{collection_name_suffix}_tenant_{tenant_id}"
    collection = service.kvstore[collection_name]

    # audit_dict, we will use this dict to trace changes per entity, ordered by the entity key id
    audit_dict = {}

    # loop through json_data and build the list of keys in keys_list
    keys_list = [json_record.get("keyid") for json_record in json_data]

    # get records
    kvrecords_dict, kvrecords = batch_find_records_by_key(collection, keys_list)

    # final records
    entities_list = []
    final_records = []

    # error counters and exceptions
    exceptions_list = []

    # loop and proceed
    for json_record in json_data:
        kvrecord_key = json_record["keyid"]
        audit_entity_changes_list = []

        # When variable_delay_policy is set for DSM/DHM, restore the lagging-class
        # default for the policy (aligns with post_disable, post_delete, post_set).
        # NOTE: allow_adaptive_delay is intentionally NOT coupled here — since
        # PR #1611 the adaptive framework handles variable-delay entities, so it is
        # an independent per-entity opt-in (default "true"). It is changed only when
        # explicitly present in the bulk-edit payload, preserving operator intent.
        if component_name in ("dsm", "dhm") and "variable_delay_policy" in json_record:
            vdp = json_record.get("variable_delay_policy")
            if vdp == "variable":
                json_record["data_override_lagging_class"] = "true"
            elif vdp == "static":
                json_record["data_override_lagging_class"] = "false"

        try:
            if kvrecord_key in kvrecords_dict:
                current_record = kvrecords_dict[kvrecord_key]

                is_different = False

                # Process only the keys provided in the json_record, while ensuring they are allowed keys
                for key, new_value in json_record.items():
                    if key in persistent_fields and new_value:
                        # set old value
                        old_value = current_record.get(key)
                        old_value, new_value = verify_type_values(old_value, new_value)

                        if old_value != new_value:
                            # audit track
                            audit_json = {
                                "field": key,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                            audit_entity_changes_list.append(audit_json)

                            # update the record
                            current_record[key] = new_value
                            is_different = True

                            # detect if we have any change in the field priority, if so set priority_updated to 1
                            if key == "priority":
                                current_record["priority_updated"] = 1

                            # detect if we have any change in the field sla_class, if so set sla_updated to 1
                            if key == "sla_class":
                                current_record["sla_updated"] = 1

                if is_different:
                    current_record["mtime"] = time.time()  # Update modification time
                    final_records.append(current_record)  # Add for batch update
                    entities_list.append(current_record.get("object"))

        except Exception as e:
            failures_count += 1
            exceptions_list.append(
                f'tenant_id="{tenant_id}", failed to update the entity, exception="{str(e)}"'
            )

        # Add the audit changes for the entity
        audit_dict[kvrecord_key] = audit_entity_changes_list

    # batch update/insert
    batch_update_collection_start = time.time()
    chunks = [final_records[i : i + 500] for i in range(0, len(final_records), 500)]
    for chunk in chunks:
        try:
            collection.data.batch_save(*chunk)
        except Exception as e:
            get_effective_logger().error(f'KVstore batch failed with exception="{str(e)}"')
            failures_count += 1
            exceptions_list.append(str(e))

    # perf counter for the batch operation
    final_records_len = len(final_records)
    get_effective_logger().info(
        f'context="perf", batch KVstore update terminated, no_records="{final_records_len}", run_time="{round((time.time() - batch_update_collection_start), 3)}"'
    )

    # Selectively patch shadow records for the modified entities (non-blocking)
    if final_records:
        # Retrieve shadow_enabled before entering thread closure
        try:
            vtenant_conf = trackme_vtenant_account_from_service(service, tenant_id)
            shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
        except Exception:
            shadow_enabled = None

        def _patch_shadow_bulk():
            try:
                service_system = client.connect(
                    token=request_info.system_authtoken,
                    owner="nobody",
                    app="trackme",
                    port=request_info.server_rest_port,
                    timeout=120,
                )
                # For bulk edit, each record may have different fields changed.
                # We pass each full updated KV record as its own "update_fields"
                # so that all modified fields are merged into the shadow.
                patch_shadow_records_full(
                    service_system,
                    tenant_id,
                    component_name,
                    final_records,
                    shadow_enabled=shadow_enabled,
                )
            except Exception as e:
                get_effective_logger().debug(
                    f'Shadow patch skipped after bulk edit: {e}, '
                    f'component="{component_name}", tenant_id="{tenant_id}"'
                )

        shadow_thread = threading.Thread(target=_patch_shadow_bulk, daemon=True)
        shadow_thread.start()

    # Record an audit change
    audits_events_list = []

    audit_status = "success" if failures_count == 0 else "failure"
    audit_message = (
        "Entity was updated successfully"
        if failures_count == 0
        else "Entity bulk update has failed"
    )

    for record in final_records:

        audits_events_list.append(
            {
                "tenant_id": tenant_id,
                "action": audit_status,
                "user": request_info.user,
                "change_type": "inline bulk edit",
                "object_id": record.get("_key"),
                "object": record.get("object"),
                "object_category": f"splk-{component_name}",
                "object_attrs": json.dumps(audit_dict.get(record.get("_key"))),
                "result": f"{audit_status}: {audit_message}",
                "comment": update_comment,
            }
        )

    # call trackme_audits_callback
    try:
        audit_response = trackme_audits_callback(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            json.dumps(audits_events_list),
        )
        get_effective_logger().info(
            f'trackme_audits_callback was called successfully, tenant_id="{tenant_id}", audits_events="{audits_events_list}", audit_response="{audit_response}"'
        )
    except Exception as e:
        get_effective_logger().error(
            f'Function trackme_audits_callback has failed, exception="{str(e)}"'
        )

    # Handle the success/failure response
    req_summary = {
        "process_count": final_records_len,
        "failures_count": failures_count,
        "entities_list": entities_list,
    }
    if failures_count == 0:
        # call trackme_register_tenant_component_summary asynchronously
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                component_name,
            ),
        )
        thread.start()

        get_effective_logger().info(
            f'entity bulk edit was successful, no_modified_records="{final_records_len}", no_records="{kvrecords}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}", results="{json.dumps(req_summary, indent=1)}"'
        )
        return req_summary, 200
    else:
        req_summary["exceptions"] = exceptions_list
        get_effective_logger().error(
            f'entity bulk edit has failed, no_modified_records="{final_records_len}", no_records="{kvrecords}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}", results="{json.dumps(req_summary, indent=1)}"'
        )
        return req_summary, 500


"""
A generic function to batch update records in a collection based on provided update fields.

:param request_info: Request metadata from the REST handler.
:param update_request_info: Information about the current request.
:param collection: The KVStore collection to update.
:param update_fields: A dictionary of fields and their new values to update.
:param update_comment: Optional comment for the update operation.
:param audit_context: The context for the audit event.
:param audit_message: The message for the audit event.
"""


def generic_batch_update(
    self,
    request_info,
    update_request_info,
    collection,
    update_fields,
    persistent_fields=None,
    component=None,
    update_comment="No comment for update.",
    audit_context="generic update",
    audit_message="Entity was updated successfully",
):
    processed_count = succcess_count = failures_count = 0

    tenant_id = update_request_info.get("tenant_id", "")
    component = update_request_info.get("component", "")
    object_list = update_request_info.get("object_list", [])
    # Defence-in-depth: every current caller pre-resolves keys_list via
    # extract_keys_list before building update_request_info, but accept the
    # object_id alias here too so a future caller passing a raw request
    # body straight through can't accidentally bypass the alias contract.
    keys_list = extract_keys_list(update_request_info, default=[])

    # normalise update_comment if necessary
    if update_comment == "N/A":
        update_comment = "No comment for update."

    # Convert comma-separated lists to Python lists if needed
    if isinstance(object_list, str):
        object_list = object_list.split(",")
    if isinstance(keys_list, str):
        keys_list = keys_list.split(",")

    # Determine query method based on input
    if object_list:
        kvrecords_dict, kvrecords = batch_find_records_by_object(
            collection, object_list
        )
    elif keys_list:
        kvrecords_dict, kvrecords = batch_find_records_by_key(collection, keys_list)
    else:
        return {
            "payload": {"error": "either object_list or keys_list must be provided"},
            "status": 500,
        }

    # audit_dict, we will use this dict to trace changes per entity, ordered by the entity key id
    audit_dict = {}

    updated_records = []

    # Strictly an updater: keys in keys_list with no matching existing record are
    # ignored. Inserting a "phantom" row from a key alone would produce an entity
    # with no `object` field, which downstream readers (priority/SLA/tags policies,
    # decision maker) cannot tolerate. See issue #1436.

    # Process existing records
    for kvrecord in kvrecords:
        # audit track
        audit_entity_changes_list = []

        for key, new_value in update_fields.items():
            if key in persistent_fields and new_value:
                # set old value
                old_value = kvrecord.get(key)
                old_value, new_value = verify_type_values(old_value, new_value)

                if old_value != new_value:
                    # audit track
                    audit_json = {
                        "field": key,
                        "old_value": old_value,
                        "new_value": new_value,
                    }
                    audit_entity_changes_list.append(audit_json)

        # detect if we have any change in the field priority, if so set priority_updated to 1 and add to updated_records
        if "priority" in update_fields:
            kvrecord["priority_updated"] = 1

        # detect if we have any change in the field sla_class, if so set sla_updated to 1
        if "sla_class" in update_fields:
            kvrecord["sla_updated"] = 1

        # Add the audit changes for the entity
        audit_dict[kvrecord.get("_key")] = audit_entity_changes_list

        kvrecord["mtime"] = time.time()
        kvrecord.update(update_fields)
        updated_records.append(kvrecord)

    # Log unmatched keys so callers passing stale/wrong identifiers are visible in
    # the logs without corrupting the collection.
    if keys_list:
        existing_keys = set(kvrecord.get("_key") for kvrecord in kvrecords)
        unmatched_keys = [k for k in keys_list if k not in existing_keys]
        if unmatched_keys:
            get_effective_logger().warning(
                f'generic_batch_update: ignoring {len(unmatched_keys)} key(s) in keys_list '
                f'with no matching record in collection, tenant_id="{tenant_id}", '
                f'component="{component}", unmatched_keys="{unmatched_keys}"'
            )

    # Update existing records in batches
    if updated_records:
        chunks = [
            updated_records[i : i + 500] for i in range(0, len(updated_records), 500)
        ]
        for chunk in chunks:
            try:
                collection.data.batch_save(*chunk)
                succcess_count += len(chunk)
            except Exception as e:
                get_effective_logger().error(f'KVstore batch save failed with exception="{str(e)}"')
                failures_count += len(chunk)

    processed_count = succcess_count + failures_count

    # Selectively patch shadow records for the modified entities (non-blocking)
    # This avoids a full 100k shadow rewrite — only the changed records are updated.
    if succcess_count > 0 and updated_records:
        all_modified_records = updated_records

        # Retrieve shadow_enabled before entering thread closure
        try:
            service_for_vtenant = client.connect(
                token=request_info.system_authtoken,
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                timeout=120,
            )
            vtenant_conf = trackme_vtenant_account_from_service(service_for_vtenant, tenant_id)
            shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
        except Exception:
            shadow_enabled = None

        def _patch_shadow():
            try:
                service_system = client.connect(
                    token=request_info.system_authtoken,
                    owner="nobody",
                    app="trackme",
                    port=request_info.server_rest_port,
                    timeout=120,
                )
                patch_shadow_records(
                    service_system,
                    tenant_id,
                    component,
                    all_modified_records,
                    update_fields,
                    shadow_enabled=shadow_enabled,
                )
            except Exception as e:
                get_effective_logger().debug(
                    f'Shadow patch skipped after bulk edit: {e}, '
                    f'component="{component}", tenant_id="{tenant_id}"'
                )

        shadow_thread = threading.Thread(target=_patch_shadow, daemon=True)
        shadow_thread.start()

    #
    # log & audit
    #

    # Record an audit change
    audits_events_list = []

    audit_status = "success" if failures_count == 0 else "failure"
    audit_message = (
        "Entity was updated successfully"
        if failures_count == 0
        else "Entity bulk update has failed"
    )

    # Audit for updated records
    for kvrecord in kvrecords:
        # Record an audit change
        if audit_dict.get(
            kvrecord.get("_key")
        ):  # only generate an audit event if a true change was made
            audits_events_list.append(
                {
                    "tenant_id": tenant_id,
                    "action": audit_status,
                    "user": request_info.user,
                    "change_type": "inline bulk edit",
                    "object_id": kvrecord.get("_key"),
                    "object": kvrecord.get("object"),
                    "object_category": f"splk-{component}",
                    "object_attrs": json.dumps(audit_dict.get(kvrecord.get("_key"))),
                    "result": f"{audit_status}: {audit_message}",
                    "comment": update_comment,
                }
            )

    try:
        audit_response = trackme_audits_callback(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            tenant_id,
            json.dumps(audits_events_list),
        )
        get_effective_logger().info(
            f'trackme_audits_callback was called successfully, tenant_id="{tenant_id}", audits_events="{audits_events_list}", audit_response="{audit_response}"'
        )
    except Exception as e:
        get_effective_logger().error(
            f'Function trackme_audits_callback has failed, exception="{str(e)}"'
        )

    # call trackme_register_tenant_component_summary
    thread = threading.Thread(
        target=self.register_component_summary_async,
        args=(
            request_info.session_key,
            request_info.server_rest_uri,
            tenant_id,
            component,
        ),
    )
    thread.start()

    # Final response
    action_results = "success" if processed_count == succcess_count else "failure"
    req_summary = {
        "action": action_results,
        "process_count": processed_count,
        "success_count": succcess_count,
        "failures_count": failures_count,
        "records": updated_records,
    }
    status = 200 if processed_count == succcess_count else 500

    # return
    return req_summary, status
