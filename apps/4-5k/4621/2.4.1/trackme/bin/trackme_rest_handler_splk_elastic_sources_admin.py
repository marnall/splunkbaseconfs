#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_elastic_sources.py"
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
import uuid

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_elastic_sources_admin",
    "trackme_rest_api_splk_elastic_sources_admin.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_create_report,
    trackme_delete_tenant_object_summary,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
    trackme_return_elastic_exec_search,
    trackme_send_to_tcm,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkElasticSourcesAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkElasticSourcesAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_elastic_sources(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_elastic_sources/admin",
            "resource_group_desc": "Endpoints related to the management of Elastic Sources (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Add new shared Elastic Source if does not exist yet
    def post_elastic_shared_add(self, request_info, **kwargs):

        # Declare
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
                        "payload": "tenant_id is required",
                        "status": 500,
                    }

                try:
                    object = resp_dict["object"]
                except Exception as e:
                    return {
                        "payload": "object is required",
                        "status": 500,
                    }

                try:
                    search_constraint = resp_dict["search_constraint"]
                except Exception as e:
                    return {
                        "payload": "search_constraint is required",
                        "status": 500,
                    }

                try:
                    search_mode = resp_dict["search_mode"]
                except Exception as e:
                    return {
                        "payload": "search_mode is required",
                        "status": 500,
                    }

                try:
                    elastic_index = resp_dict["elastic_index"]
                except Exception as e:
                    return {
                        "payload": "elastic_index is required",
                        "status": 500,
                    }

                try:
                    elastic_sourcetype = resp_dict["elastic_sourcetype"]
                except Exception as e:
                    return {
                        "payload": "elastic_sourcetype is required",
                        "status": 500,
                    }

                # earliest and latest are optional, if unset we define default values
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-4h"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "+4h"

                # check mode
                if search_mode not in (
                    "tstats",
                    "raw",
                    "from",
                    "mstats",
                    "mpreview",
                    "remote_tstats",
                    "remote_raw",
                    "remote_from",
                    "remote_mstats",
                    "remote_mpreview",
                ):
                    logger.error(f'invalid mode specified="{search_mode}"')
                    return {
                        "payload": f'invalid mode specified="{search_mode}"',
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint create a new shared Elastic Source, if the entity already exists it will be updated using the data provided, it requires a POST call with the following information:",
                "resource_desc": "Get Elastic Sources",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_elastic_sources/admin/elastic_shared_add\" body=\"{'tenant_id': 'mytenant', 'object': 'mysource', 'search_constraint': 'index=net*', 'search_mode': 'tstats', 'elastic_index': 'myindex', 'elastic_sourcetype': 'mysourcetype', 'earliest_time': '-4h', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "(required) name of the Elastic Source",
                        "search_constraint": "(required) the SPL code for this entity, double quotes need to be escaped",
                        "search_mode": "(required) the search mode, valid options are tstats / raw / from / mstats / mpreview / remote_tstats / remote_raw / remote_from / remote_mstats / remote_mpreview",
                        "elastic_index": "(required) pseudo index value, this value will be used in the UI but has no impacts on the search",
                        "elastic_sourcetype": "(required) pseudo sourcetype value name, this value will be used in the UI but has no impacts on the search",
                        "earliest_time": "(optional) earliest time for the scheduled report definition, if unset will be defined to -4h",
                        "latest_time": "(optional) latest time for the scheduled report definition, if unset will be defined to -4h",
                        "update_comment": "(optional) a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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
            "object": object,
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
            collection_name = "kv_trackme_dsm_elastic_shared_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # This record exists already
                response = {
                    "action": "failure",
                    "response": "conflict, a record for this object exists already",
                    "record": kvrecord,
                }

                logger.error(json.dumps(response), indent=2)
                return {"payload": response, "status": 500}

            else:
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
                            "/services/trackme/v2/splk_elastic_sources/admin/elastic_shared_add",
                        )
                        logger.info(f"trackme_send_to_tcm was successfully executed")
                    except Exception as e:
                        logger.error(
                            f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                        )

                # This record does not exist yet
                elastic_record = {
                    "object": str(object),
                    "search_constraint": str(search_constraint),
                    "search_mode": str(search_mode),
                    "elastic_index": elastic_index,
                    "elastic_sourcetype": elastic_sourcetype,
                    "earliest": earliest_time,
                    "latest": latest_time,
                }

                # Insert the record
                collection.data.insert(json.dumps(elastic_record, indent=1))

                # Get record
                record = collection.data.query(query=json.dumps(query_string))
                record = json.dumps(record[0], indent=1)

                # Record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "add elastic source tracker",
                    str(object),
                    "elastic_sources_tracker",
                    str(record),
                    "The new elastic source was created successfully",
                    str(update_comment),
                )

                logger.info("success for record=" + str(record))
                return {"payload": str(record), "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Update an existing shared Elastic Source
    def post_elastic_shared_update(self, request_info, **kwargs):

        # Declare
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
                        "payload": "tenant_id is required",
                        "status": 500,
                    }

                try:
                    object = resp_dict["object"]
                except Exception as e:
                    return {
                        "payload": "object is required",
                        "status": 500,
                    }

                try:
                    search_constraint = resp_dict["search_constraint"]
                except Exception as e:
                    return {
                        "payload": "search_constraint is required",
                        "status": 500,
                    }

                try:
                    search_mode = resp_dict["search_mode"]
                except Exception as e:
                    return {
                        "payload": "search_mode is required",
                        "status": 500,
                    }

                try:
                    elastic_index = resp_dict["elastic_index"]
                except Exception as e:
                    return {
                        "payload": "elastic_index is required",
                        "status": 500,
                    }

                try:
                    elastic_sourcetype = resp_dict["elastic_sourcetype"]
                except Exception as e:
                    return {
                        "payload": "elastic_sourcetype is required",
                        "status": 500,
                    }

                # earliest and latest are optional, if unset we define default values
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-4h"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "+4h"

                # check mode
                if search_mode not in (
                    "tstats",
                    "raw",
                    "from",
                    "mstats",
                    "mpreview",
                    "remote_tstats",
                    "remote_raw",
                    "remote_from",
                    "remote_mstats",
                    "remote_mpreview",
                ):
                    logger.error(f'invalid mode specified="{search_mode}"')
                    return {
                        "payload": f'invalid mode specified="{search_mode}"',
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates an existing shared Elastic Source, it requires a POST call with the following information:",
                "resource_desc": "Update Elastic Sources",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_elastic_sources/admin/elastic_shared_update\" body=\"{'tenant_id': 'mytenant', 'object': 'mysource', 'search_constraint': 'index=net*', 'search_mode': 'tstats', 'elastic_index': 'myindex', 'elastic_sourcetype': 'mysourcetype', 'earliest_time': '-4h', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "(required) name of the Elastic Source to update",
                        "search_constraint": "(required) the SPL code for this entity, double quotes need to be escaped",
                        "search_mode": "(required) the search mode, valid options are tstats / raw / from / mstats / mpreview / remote_tstats / remote_raw / remote_from / remote_mstats / remote_mpreview",
                        "elastic_index": "(required) pseudo index value, this value will be used in the UI but has no impacts on the search",
                        "elastic_sourcetype": "(required) pseudo sourcetype value name, this value will be used in the UI but has no impacts on the search",
                        "earliest_time": "(optional) earliest time for the scheduled report definition, if unset will be defined to -4h",
                        "latest_time": "(optional) latest time for the scheduled report definition, if unset will be defined to +4h",
                        "update_comment": "(optional) a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
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
            "object": object,
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

        try:
            # Data collection
            collection_name = "kv_trackme_dsm_elastic_shared_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            # Get the current record
            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")
            except Exception as e:
                key = None

            if not key:
                response = {
                    "action": "failure",
                    "response": "the record for this object does not exist",
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 404}

            # check if TCM is enabled in receiver mode
            trackme_conf = trackme_reqinfo(
                request_info.system_authtoken, request_info.server_rest_uri
            )
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
                        "/services/trackme/v2/splk_elastic_sources/admin/elastic_shared_update",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # Update the record
            elastic_record = {
                "object": str(object),
                "search_constraint": str(search_constraint),
                "search_mode": str(search_mode),
                "elastic_index": elastic_index,
                "elastic_sourcetype": elastic_sourcetype,
                "earliest": earliest_time,
                "latest": latest_time,
            }

            collection.data.update(key, json.dumps(elastic_record, indent=1))

            # Get updated record
            record = collection.data.query(query=json.dumps(query_string))
            record = json.dumps(record[0], indent=1)

            # Record an audit change
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                tenant_id,
                request_info.user,
                "success",
                "update elastic source tracker",
                str(object),
                "elastic_sources_tracker",
                str(record),
                "The elastic source was updated successfully",
                str(update_comment),
            )

            logger.info("success for record=" + str(record))
            return {"payload": str(record), "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Add new shared Elastic Source if does not exist yet
    def post_elastic_dedicated_add(self, request_info, **kwargs):

        # Declare
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
                        "payload": "tenant_id is required",
                        "status": 500,
                    }

                try:
                    object = resp_dict["object"]
                except Exception as e:
                    return {
                        "payload": "object is required",
                        "status": 500,
                    }

                try:
                    search_constraint = resp_dict["search_constraint"]
                except Exception as e:
                    return {
                        "payload": "search_constraint is required",
                        "status": 500,
                    }

                try:
                    search_mode = resp_dict["search_mode"]
                except Exception as e:
                    return {
                        "payload": "search_mode is required",
                        "status": 500,
                    }

                try:
                    elastic_index = resp_dict["elastic_index"]
                except Exception as e:
                    return {
                        "payload": "elastic_index is required",
                        "status": 500,
                    }

                try:
                    elastic_sourcetype = resp_dict["elastic_sourcetype"]
                except Exception as e:
                    return {
                        "payload": "elastic_sourcetype is required",
                        "status": 500,
                    }

                # Splunk owner, if not specified defaults to admin
                try:
                    owner = resp_dict["owner"]
                except Exception as e:
                    owner = None

                # earliest and latest are optional, if unset we define default values
                try:
                    earliest_time = resp_dict["earliest_time"]
                except Exception as e:
                    earliest_time = "-4h"

                try:
                    latest_time = resp_dict["latest_time"]
                except Exception as e:
                    latest_time = "+4h"

                # check mode
                if search_mode not in (
                    "tstats",
                    "raw",
                    "from",
                    "mstats",
                    "mpreview",
                    "remote_tstats",
                    "remote_raw",
                    "remote_from",
                    "remote_mstats",
                    "remote_mpreview",
                ):
                    logger.error(f'invalid mode specified="{search_mode}"')
                    return {
                        "payload": f'invalid mode specified="{search_mode}"',
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint create a new shared Elastic Source, if the entity already exists it will be updated using the data provided, it requires a POST call with the following information:",
                "resource_desc": "Get Elastic Sources",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_elastic_sources/admin/elastic_dedicated_add\" body=\"{'tenant_id': 'mytenant', 'object': 'mysource', 'search_constraint': 'index=net*', 'search_mode': 'tstats', 'elastic_index': 'myindex', 'elastic_sourcetype': 'mysourcetype', 'earliest_time': '-4h', 'latest_time': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "(required) name of the Elastic Source",
                        "search_constraint": "(required) the SPL code for this entity, double quotes need to be escaped",
                        "search_mode": "(required) the search mode, valid options are tstats / raw / from / mstats / mpreview / remote_tstats / remote_raw / remote_from / remote_mstats / remote_mpreview",
                        "elastic_index": "(required) pseudo index value, this value will be used in the UI but has no impacts on the search",
                        "elastic_sourcetype": "(required) pseudo sourcetype value name, this value will be used in the UI but has no impacts on the search",
                        "earliest_time": "(optional) earliest time for the scheduled report definition, if unset will be defined to -4h",
                        "latest_time": "(optional) latest time for the scheduled report definition, if unset will be defined to -4h",
                        "owner": "(optional) the Splunk user owning the objects to be created, if not specified defaults to the owner set for the tenant",
                        "update_comment": "(optional) a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # elastic_report is generated during ops

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define the KV query
        query_string = {
            "object": object,
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

        # TrackMe sharing level
        trackme_default_sharing = trackme_conf["trackme_conf"]["trackme_general"][
            "trackme_default_sharing"
        ]

        # Retrieve the virtual tenant record to access acl
        collection_vtenants_name = "kv_trackme_virtual_tenants"
        collection_vtenants = service.kvstore[collection_vtenants_name]

        # Define the KV query search string
        vtenant_query_string = {
            "tenant_id": tenant_id,
        }

        # Get the tenant
        try:
            vtenant_record = collection_vtenants.data.query(
                query=json.dumps(vtenant_query_string)
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
        # verify the owner
        if not owner:
            owner = vtenant_record.get("tenant_owner")

        # gen a uuid
        uuid_value = uuid.uuid4().hex[:5]

        # Elastic Source wrapper
        wrapper_name = (
            f"trackme_dsm_dedicated_elastic_wrapper_tenant_{tenant_id}_{uuid_value}"
        )

        # report name len is 100 chars max
        wrapper_name = wrapper_name[:100]

        # Elastic Source tracker
        tracker_name = (
            f"trackme_dsm_dedicated_elastic_tracker_tenant_{tenant_id}_{uuid_value}"
        )

        # report name len is 100 chars max
        tracker_name = tracker_name[:100]

        # define the report root search depending on various conditions
        elastic_report_root_search = None

        #
        # Set the search depending on its language
        #

        try:
            elastic_report_root_search = trackme_return_elastic_exec_search(
                search_mode,
                search_constraint,
                object,
                elastic_index,
                elastic_sourcetype,
                tenant_id,
                "True",
                wrapper_name,
            )
            logger.debug(f'elastic_report_root_search="{elastic_report_root_search}"')
        except Exception as e:
            return {
                "payload": f'Unexpected error encountered, the search could not be defined properly, search_mode="{search_mode}", search_constraint="{search_constraint}", exception="{str(e)}"',
                "status": 500,
            }

        # debug
        logger.debug(f'elastic_report_root_search="{elastic_report_root_search}"')

        # Data collection
        collection_name = "kv_trackme_dsm_elastic_dedicated_tenant_" + str(tenant_id)
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            kvrecord = collection.data.query(query=json.dumps(query_string))[0]
            key = kvrecord.get("_key")

        except Exception as e:
            key = None

        # Render result
        if key:
            # This Elastic Source exists already, the report and record will be updated with the POST data

            # Get the tracker name from the record
            tracker_name = kvrecord.get("elastic_report")

            logger.error(
                f'tenant_id="{tenant_id}", conflict an Elastic Source with the same name exists already, tracker_name="{tracker_name}"'
            )
            return {
                "payload": {
                    "tenant_id": tenant_id,
                    "tracker_name": tracker_name,
                    "action": "failure",
                    "exception": "conflict an Elastic Source with the same name exists already",
                },
                "status": 500,
            }

        else:
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
                        "/services/trackme/v2/splk_elastic_sources/admin/elastic_dedicated_add",
                    )
                    logger.info(f"trackme_send_to_tcm was successfully executed")
                except Exception as e:
                    logger.error(
                        f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                    )

            # This tracker does not exist yet
            try:
                kwargs = {
                    "description": "Dedicated elastic wrapper for: "
                    + str(tracker_name),
                    "is_scheduled": False,
                    "dispatch.earliest_time": str(earliest_time),
                    "dispatch.latest_time": str(latest_time),
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
                    wrapper_name,
                    elastic_report_root_search,
                    kwargs,
                    report_acl,
                )

                # Create the Elastic Source tracker
                tracker_root_search = f'| trackmetrackerexecutor tenant_id="{tenant_id}", component="splk-dsm" report="{wrapper_name}" alert_no_results=True'

                # create a new report
                kwargs = {
                    "description": "Dedicated elastic tracker for data source",
                    "is_scheduled": True,
                    "schedule_window": "5",
                    "cron_schedule": "*/5 * * * *",
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
                    tracker_name,
                    tracker_root_search,
                    kwargs,
                    report_acl,
                )

                # Insert the record
                collection.data.insert(
                    json.dumps(
                        {
                            "object": str(object),
                            "search_constraint": str(search_constraint),
                            "search_mode": str(search_mode),
                            "elastic_index": str(elastic_index),
                            "elastic_sourcetype": str(elastic_sourcetype),
                            "elastic_wrapper": wrapper_create_report.get("report_name"),
                            "elastic_report": tracker_create_report.get("report_name"),
                        }
                    )
                )

                # Get record
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]

                # Audit
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "add elastic source tracker",
                    str(object),
                    "elastic_sources_tracker",
                    str(kvrecord),
                    "The new elastic source was created successfully",
                    str(update_comment),
                )

                return {"payload": kvrecord, "status": 200}

            except Exception as e:
                response = {
                    "action": "failure",
                    "response": f'an exception was encountered, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

    # Delete elastic source
    def post_elastic_delete(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        elastic_entities_list = None
        elastic_type = None
        query_string = None
        tracker_name = None

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
                        "payload": "tenant_id is required",
                        "status": 500,
                    }

                try:
                    elastic_type = resp_dict["elastic_type"]
                except Exception as e:
                    return {
                        "payload": "elastic_type is required",
                        "status": 500,
                    }

                if not elastic_type in ("shared", "dedicated"):
                    return {
                        "payload": {
                            "tenant_id": tenant_id,
                            "elastic_type": elastic_type,
                            "response": "Unsupported value for elastic_type, valid options are: shared | dedicated",
                        },
                        "status": 500,
                    }

                try:
                    elastic_entities_list = resp_dict["elastic_entities_list"]
                except Exception as e:
                    return {
                        "payload": "elastic_entities_list is required",
                        "status": 500,
                    }

                # Handle as a CSV list of keys, if not a list already
                if not isinstance(elastic_entities_list, list):
                    elastic_entities_list = [x.strip() for x in elastic_entities_list.split(",") if x.strip()]
                else:
                    # Filter out empty strings from existing list
                    elastic_entities_list = [x.strip() if isinstance(x, str) else x for x in elastic_entities_list if (x.strip() if isinstance(x, str) else bool(x))]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a dedicated Elastic Source, it requires a POST call with the following information:",
                "resource_desc": "Get Elastic Sources",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_elastic_sources/admin/elastic_delete\" body=\"{'tenant_id': 'mytenant', 'elastic_type': 'dedicated', 'elastic_entities_list': 'test001,test002'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "elastic_type": "(required) The type of elastic sources, valid options are: shared | dedicated",
                        "elastic_entities_list": "(required) Comma separated list of Elastic Source entities to be deleted",
                        "update_comment": "(optional) a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # tracker_name is extracted from the KVstore record

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

        for elastic_entity in elastic_entities_list:
            # this operation will be considered to be successful only no failures were encountered
            # any failure encountered will be added to the record summary for that entity
            sub_failures_count = 0

            # Define the KV query
            query_string = {
                "object": elastic_entity,
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
                # Elastic sources collection
                if elastic_type == "shared":
                    collection_elastic_name = (
                        "kv_trackme_dsm_elastic_shared_tenant_" + str(tenant_id)
                    )
                elif elastic_type == "dedicated":
                    collection_elastic_name = (
                        "kv_trackme_dsm_elastic_dedicated_tenant_" + str(tenant_id)
                    )
                collection_elsstic = service.kvstore[collection_elastic_name]

                # Data sources collection
                collection_dsm_name = "kv_trackme_dsm_tenant_" + str(tenant_id)
                collection_dsm = service.kvstore[collection_dsm_name]

                # Get the elastic entity record
                try:
                    elastic_entity_record = collection_elsstic.data.query(
                        query=json.dumps(query_string)
                    )
                    elastic_entity_key = elastic_entity_record[0].get("_key")

                    if elastic_type == "dedicated":
                        # Get the wrapper & tracker names
                        wrapper_name = elastic_entity_record[0].get("elastic_wrapper")
                        tracker_name = elastic_entity_record[0].get("elastic_report")

                except Exception as e:
                    elastic_entity_key = None

                # Get the dsm entity record
                try:
                    dsm_entity_record = collection_dsm.data.query(
                        query=json.dumps(query_string)
                    )
                    dsm_entity_key = dsm_entity_record[0].get("_key")

                except Exception as e:
                    dsm_entity_key = None

                # If the Elsstic Source entity was found
                if elastic_entity_key is not None and len(elastic_entity_key) > 2:
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
                                "/services/trackme/v2/splk_elastic_sources/admin/elastic_delete",
                            )
                            logger.info(
                                f"trackme_send_to_tcm was successfully executed"
                            )
                        except Exception as e:
                            logger.error(
                                f'trackme_send_to_tcm has failed with exception="{str(e)}"'
                            )

                    if elastic_type == "dedicated":
                        # Attempt to remove the tracker
                        try:
                            service.saved_searches.delete(str(tracker_name))
                            logger.info(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", the tracker was successfully removed, tracker_name="{tracker_name}"'
                            )

                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to remove the tracker, tracker_name="{tracker_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "elastic_entity": elastic_entity,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to remove the tracker, tracker_name="{tracker_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                        # Attempt to remove the wrapper
                        try:
                            service.saved_searches.delete(str(wrapper_name))
                            logger.info(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", the wrapper was successfully removed, wrapper_name="{wrapper_name}"'
                            )

                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to remove the wrapper, wrapper_name="{wrapper_name}", exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "elastic_entity": elastic_entity,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to remove the wrapper, wrapper_name="{wrapper_name}", exception="{str(e)}"',
                            }
                            records.append(result)

                        # Attempt to purge the register summary object
                        try:
                            delete_register_summary = (
                                trackme_delete_tenant_object_summary(
                                    request_info.system_authtoken,
                                    request_info.server_rest_uri,
                                    tenant_id,
                                    "splk-dsm",
                                    wrapper_name,
                                )
                            )
                        except Exception as e:
                            logger.error(
                                f'exception encountered while calling function trackme_delete_tenant_object_summary, exception="{str(e)}"'
                            )

                    # Attempt to remove the Elastic record
                    try:
                        collection_elsstic.data.delete(
                            json.dumps({"_key": elastic_entity_key})
                        )
                        logger.info(
                            f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", the Elastic entity record was deleted successfully, record="{json.dumps(elastic_entity_record, indent=0)}"'
                        )

                    except Exception as e:
                        logger.error(
                            f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"'
                        )

                        sub_failures_count += 1
                        result = {
                            "elastic_entity": elastic_entity,
                            "action": "delete",
                            "result": "failure",
                            "exception": f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to delete the entity record in the Elastic Source dedicated KVstore collection, exception="{str(e)}"',
                        }
                        records.append(result)

                    # Attempt to remove the dsm entity, if it exists
                    if dsm_entity_key:
                        try:
                            collection_dsm.data.delete(
                                json.dumps({"_key": dsm_entity_key})
                            )
                            logger.info(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", the dsm entity record was deleted successfully, record="{json.dumps(dsm_entity_record, indent=0)}"'
                            )
                        except Exception as e:
                            logger.error(
                                f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", exception encountered while attempting to delete the KVstore record, exception="{str(e)}"'
                            )

                            sub_failures_count += 1
                            result = {
                                "elastic_entity": elastic_entity,
                                "action": "delete",
                                "result": "failure",
                                "exception": f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", failed to delete the Elastic entity record in thedsm KVstore collection, exception="{str(e)}"',
                            }
                            records.append(result)
                    else:
                        logger.info(
                            f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", could not find the corresponding entity in the dsm KVstore collection'
                        )

                    # Handle the sub operation results
                    if sub_failures_count == 0:
                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # append for summary
                        result = {
                            "object": elastic_entity,
                            "action": "delete",
                            "result": "success",
                            "message": f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", The Elastic Source entity and its associated objects were successfully deleted',
                        }
                        records.append(result)

                        # audit record
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "delete elastic entity",
                            str(elastic_entity),
                            "elastic_sources_tracker",
                            str(json.dumps(elastic_entity_record, indent=2)),
                            "The Elastic Source entity and its associated objects were successfully deleted",
                            str(update_comment),
                        )

                        # log
                        logger.info(
                            f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", The Elastic Source entity and its associated objects were successfully deleted'
                        )

                else:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    logger.error(
                        f'tenant_id="{tenant_id}", elastic_entity="{elastic_entity}", the resource was not found or the request is incorrect'
                    )

                    # append for summary
                    result = {
                        "elastic_entity": elastic_entity,
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
                    "elastic_entity": elastic_entity,
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
