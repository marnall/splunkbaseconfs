#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_replica_trackers_admin.py"
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
import sys
import time
import uuid
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
    "trackme.rest.splk_replica_trackers_admin",
    "trackme_rest_api_splk_replica_trackers_admin.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import (
    trackme_audit_event,
    trackme_create_macro,
    trackme_create_report,
    trackme_delete_macro,
    trackme_delete_tenant_object_summary,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_send_to_tcm,
)
from trackme_libs_utils import sanitize_spl_input

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkReplicaTrackerAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkReplicaTrackerAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_replica_trackers(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_replica_trackers/admin",
            "resource_group_desc": "Endpoints related to the management of Replica trackers (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Create a replica tracker
    def post_replica_tracker_create(self, request_info, **kwargs):
        # args
        tenant_id = None
        component = None
        source_tenant_id = None
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

                # source_tenant_id
                source_tenant_id = resp_dict["source_tenant_id"]

                # component
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm", "flx", "fqm", "wlk"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm|flx|fqm|wlk'
                        },
                        "status": 500,
                    }

                # the root constraint of the tracker
                root_constraint = sanitize_spl_input(resp_dict["root_constraint"])

                #
                # optional args
                #

                try:
                    cron_schedule = resp_dict["cron_schedule"]
                except Exception as e:
                    cron_schedule = "*/5 * * * *"

                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # earliest_time and latest_time are not relevant for a replica tracker
                earliest_time = "-5m"
                latest_time = "now"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint allows creating a replica tracker, it requires a POST call with the following information:",
                "resource_desc": "Create a new replica tracker",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_replica_trackers/admin/replica_tracker_create\" body=\"{'tenant_id': 'mytenant', 'source_tenant_id': 'my_source_tenant', 'component': 'dsm', 'root_constraint': 'object=*'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "source_tenant_id": "The source tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm | flx | fqm | wlk",
                        "root_constraint": "the tracker report root search constraint, to define search filters scoping the data set",
                        "owner": "Optional, the Splunk user owning the objects to be created, defaults to the owner set for the tenant",
                        "cron_schedule": "Optional, the cron schedule, defaults to every 5 minutes",
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
                        "/services/trackme/v2/splk_replica_trackers/admin/replica_tracker_create",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # verify the owner
            if not owner:
                owner = vtenant_record.get("tenant_owner")

            # create a tracker_name
            tracker_name = f"replica_{uuid.uuid4().hex[:5]}"

            #
            # create the replica root constraint macro
            #

            root_constraint_macro = (
                "trackme_%s_replica_root_constraint_%s_tenant_%s"
                % (component, tracker_name, tenant_id)
            )
            macro_acl = {
                "owner": owner,
                "sharing": trackme_default_sharing,
                "perms.write": vtenant_record.get("tenant_roles_admin"),
                "perms.read": f"{vtenant_record.get('tenant_roles_user')},{vtenant_record.get('tenant_roles_power')}",
            }
            macro_result = trackme_create_macro(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                root_constraint_macro,
                root_constraint,
                owner,
                macro_acl,
            )

            #
            # create the wrapper
            #

            report_name = (
                f"trackme_{component}_replica_{tracker_name}_wrapper_tenant_{tenant_id}"
            )
            report_search = (
                f"| inputlookup trackme_{component}_tenant_{source_tenant_id} | search `{root_constraint_macro}` | eval key=_key"
                + f'\n| trackmereplicator component="{component}" source_tenant_id="{source_tenant_id}" target_tenant_id="{tenant_id}" key_field="key"'
            )

            # create a new report
            report_properties = {
                "description": "TrackMe replica wrapper",
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
                report_search,
                report_properties,
                report_acl,
            )

            #
            # Splunkd API needs a couple of seconds to refresh while KOs are created
            #

            # set max failed re-attempt
            max_failures_count = 24
            sleep_time = 5
            creation_success = False
            current_failures_count = 0

            while current_failures_count < max_failures_count and not creation_success:
                try:
                    newtracker = service.saved_searches[report_name]
                    logger.info(
                        f'action="success", replica tracker was successfully created, report_name="{report_name}"'
                    )
                    creation_success = True
                    break

                except Exception as e:
                    # We except this sentence in the exception if the API is not ready yet
                    logger.warning(
                        f'temporary failure, the report is not yet available, will sleep and re-attempt, report report_name="{report_name}"'
                    )
                    time.sleep(sleep_time)
                    current_failures_count += 1

                    if current_failures_count >= max_failures_count:
                        logger.error(
                            f'max attempt reached, failure to create report report_name="{report_name}" with exception="{str(e)}"'
                        )
                        break

            # sleep 2 sec as an additional safety
            time.sleep(2)

            #
            # END
            #

            audit_record = {
                "wrapper_report": wrapper_create_report.get("report_name"),
                "root_constraint_macro": str(root_constraint_macro),
                "root_constraint": str(root_constraint),
                "tracker_name": tracker_name,
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
                    tenant_replica_objects = vtenant_record.get(
                        "tenant_replica_objects"
                    )

                    # logger.debug
                    logger.debug(f'tenant_replica_objects="{tenant_replica_objects}"')
                except Exception as e:
                    tenant_replica_objects = None

                # add to existing dict
                if tenant_replica_objects and tenant_replica_objects != "None":
                    vtenant_dict = json.loads(tenant_replica_objects)
                    logger.info(f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"')

                    report1 = wrapper_create_report.get("report_name")
                    macro1 = str(root_constraint_macro)

                    try:
                        reports = vtenant_dict["reports"]
                    except Exception as e:
                        reports = []

                    try:
                        macros = vtenant_dict["macros"]
                    except Exception as e:
                        macros = []

                    reports.append(str(report1))
                    macros.append(str(macro1))

                    vtenant_dict = dict(
                        [
                            ("reports", reports),
                            ("macros", macros),
                        ]
                    )

                # empty dict
                else:
                    report1 = wrapper_create_report.get("report_name")
                    macro1 = str(root_constraint_macro)

                    reports = []
                    reports.append(str(report1))

                    macros = []
                    macros.append(macro1)

                    vtenant_dict = dict(
                        [
                            ("reports", reports),
                            ("macros", macros),
                        ]
                    )

                try:
                    vtenant_record["tenant_replica_objects"] = json.dumps(
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

                # Record the new replica component in the replica collection
                collection_replica_name = (
                    "kv_trackme_common_replica_trackers_tenant_" + str(tenant_id)
                )
                collection_replica = service.kvstore[collection_replica_name]

                reports = []
                reports.append(str(report1))

                macros = []
                macros.append(str(macro1))

                properties = []
                properties_dict = {
                    "root_constraint_macro": str(root_constraint_macro),
                    "root_constraint": str(root_constraint),
                    "tracker_name": tracker_name,
                }

                properties.append(properties_dict)

                replica_dict = dict(
                    [
                        ("reports", reports),
                        ("macros", macros),
                        ("properties", properties),
                    ]
                )

                try:
                    collection_replica.data.insert(
                        json.dumps(
                            {
                                "_key": hashlib.sha256(
                                    tracker_name.encode("utf-8")
                                ).hexdigest(),
                                "tracker_name": tracker_name,
                                "knowledge_objects": json.dumps(replica_dict, indent=1),
                            }
                        )
                    )
                except Exception as e:
                    logger.error(
                        f'tenant_id="{tenant_id}", tracker_name="{tracker_name}", failure while trying to insert the replica KVstore record, exception="{str(e)}"'
                    )

            # Record an audit change
            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "add replica tracker",
                    "trackme_" + str(component) + "_replica_" + str(tracker_name),
                    "replica_tracker",
                    str(audit_record),
                    "The replica tracker was created successfully",
                    str(update_comment),
                )
            except Exception as e:
                logger.error(
                    f'failed to generate an audit event with exception="{str(e)}"'
                )

            # final return
            logger.info(json.dumps(audit_record, indent=2))
            return {"payload": audit_record, "status": 200}

    # Remove a replica tracker and associated objects
    def post_replica_tracker_delete(self, request_info, **kwargs):
        # By tracker_name
        tenant_id = None
        component = None
        replica_trackers_list = None
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
                replica_trackers_list = resp_dict["replica_trackers_list"]
                # Handle as a CSV list of keys, it not already a list
                if not isinstance(replica_trackers_list, list):
                    replica_trackers_list = [x.strip() for x in replica_trackers_list.split(",") if x.strip()]
                else:
                    # Filter out empty strings from existing list
                    replica_trackers_list = [x.strip() if isinstance(x, str) else x for x in replica_trackers_list if (x.strip() if isinstance(x, str) else bool(x))]
                # get component
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm", "flx", "fqm", "wlk"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm|flx|fqm|wlk'
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs the deletion of a replica tracker and associated objects, it requires a POST call with the following information:",
                "resource_desc": "Delete a replica tracker and associated objects",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_replica_trackers/admin/replica_tracker_delete\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'replica_trackers_list': 'test:001,test:002'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm",
                        "replica_trackers_list": "comma separated list of replica entities to be deleted, for each submitted entity, all related objects will be purged",
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
        for replica_tracker in replica_trackers_list:
            # this operation will be considered to be successful only no failures were encountered
            # any failure encountered will be added to the record summary for that entity
            sub_failures_count = 0

            # Define the KV query
            query_string = {
                "tracker_name": replica_tracker,
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
                collection_name = (
                    f"kv_trackme_common_replica_trackers_tenant_{tenant_id}"
                )
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    replica_record = collection.data.query(
                        query=json.dumps(query_string)
                    )
                    key = replica_record[0].get("_key")

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
                                "/services/trackme/v2/splk_replica_trackers/admin/replica_tracker_delete",
                            )
                            logger.info(
                                f"trackme_send_to_tcm was successfully executed"
                            )
                        except Exception as e:
                            logger.error(
                                f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                            )

                    # load the knowledge object dict
                    tenant_replica_objects = json.loads(
                        replica_record[0].get("knowledge_objects")
                    )
                    logger.debug(
                        f'tenant_replica_objects="{json.dumps(tenant_replica_objects, indent=1)}"'
                    )

                    # Step 1: delete knowledge objects
                    try:
                        reports_list = tenant_replica_objects["reports"]
                    except Exception as e:
                        reports_list = []
                    logger.debug(f'reports_list="{reports_list}"')

                    try:
                        macros_list = tenant_replica_objects["macros"]
                    except Exception as e:
                        macros_list = []
                    logger.debug(f'macros_list="{macros_list}"')

                    # Delete all reports
                    for report_name in reports_list:
                        logger.info(
                            f'tenant_id="{tenant_id}", attempting removal of report="{report_name}"'
                        )
                        try:
                            service.saved_searches.delete(str(report_name))
                            logger.info(
                                f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", action="success", the report was successfully removed, report_name="{report_name}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "replica_tracker": replica_tracker,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", failed to remove the report, report_name="{report_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                    # Delete all macros
                    for macro_name in macros_list:
                        logger.info(
                            f'tenant_id="{tenant_id}", attempting removal of macro="{macro_name}"'
                        )
                        try:
                            action = trackme_delete_macro(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                macro_name,
                            )
                            logger.info(
                                f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", action="success", the macro was successfully removed, macro_name="{macro_name}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", failed to remove the macro, macro_name="{macro_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "replica_tracker": replica_tracker,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", failed to remove the macro, macro_name="{macro_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                    # Step 2: delete the KVstore record

                    # Remove the record
                    try:
                        collection.data.delete(json.dumps({"_key": key}))

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", tracker_name="{replica_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"'
                        )
                        sub_failures_count += 1
                        result = {
                            "tracker_name": replica_tracker,
                            "action": "delete",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", tracker_name="{replica_tracker}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"',
                        }
                        records.append(result)

                    # Step 3: delete the replica knowledge from the tenant

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
                            tenant_replica_objects = vtenant_record.get(
                                "tenant_replica_objects"
                            )
                            # logger.debug
                            logger.debug(
                                f'tenant_replica_objects="{tenant_replica_objects}"'
                            )
                        except Exception as e:
                            tenant_replica_objects = None

                        # remove from the dict
                        if tenant_replica_objects and tenant_replica_objects != "None":
                            vtenant_dict = json.loads(tenant_replica_objects)
                            logger.debug(
                                f'vtenant_dict="{json.dumps(vtenant_dict, indent=1)}"'
                            )

                            report1 = f"trackme_{component}_replica_{replica_tracker}_wrapper_tenant_{tenant_id}"

                            reports = vtenant_dict["reports"]
                            try:
                                reports.remove(report1)
                            except ValueError:
                                logger.warning(
                                    f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", report="{report1}" not found in tenant_replica_objects, skipping removal'
                                )

                            # macros were added in a later version
                            macro1 = (
                                "trackme_%s_replica_root_constraint_%s_tenant_%s"
                                % (component, replica_tracker, tenant_id)
                            )

                            try:
                                macros = vtenant_dict["macros"]
                                try:
                                    macros.remove(str(macro1))
                                except ValueError:
                                    logger.warning(
                                        f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", macro="{macro1}" not found in tenant_replica_objects, skipping removal'
                                    )

                            except Exception as e:
                                macros = []

                            vtenant_dict = dict(
                                [
                                    ("reports", reports),
                                    ("macros", macros),
                                ]
                            )

                            # Update the KVstore
                            try:
                                vtenant_record["tenant_replica_objects"] = json.dumps(
                                    vtenant_dict, indent=2
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
                            "splk-" + str(component),
                            "trackme_"
                            + str(component)
                            + "_replica_"
                            + str(replica_tracker)
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
                            "remove replica tracker",
                            str(replica_tracker),
                            "replica_tracker",
                            str(json.dumps(replica_record, indent=2)),
                            "The replica tracker and its associated objects were successfully deleted",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    logger.info(
                        f'tenant_id="{tenant_id}", tracker_name="{replica_tracker}", The replica tracker and its associated objects were successfully deleted'
                    )

                    # Handle the sub operation results
                    if sub_failures_count == 0:
                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "tracker_name": replica_tracker,
                            "action": "delete",
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", replica_tracker="{replica_tracker}", The replica tracker and its associated objects were successfully deleted',
                        }
                        records.append(result)

                else:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    logger.error(
                        f'tenant_id="{tenant_id}", tracker_name="{replica_tracker}", the resource was not found or the request is incorrect'
                    )

                    # append for summary
                    result = {
                        "tracker_name": replica_tracker,
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
                    "tracker_name": replica_tracker,
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
