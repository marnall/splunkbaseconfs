#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_audit.py"
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
import time
import datetime
import hashlib

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.audit", "trackme_rest_api_audit.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_idx_for_tenant, trackme_parse_describe_flag, trackme_reqinfo

# import trackme libs audit
from trackme_libs_audit import trackme_audit_gen, trackme_handler_events_gen

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAudit_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAudit_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_audit(self, request_info, **kwargs):
        response = {
            "resource_group_name": "audit",
            "resource_group_desc": "These endpoints provide functionality to generate audit events in TrackMe tenants. They are used internally and can also be used to generate additional audit events in TrackMe sub-systems",
        }

        return {"payload": response, "status": 200}

    # Register multiple audit events at once
    def post_audit_events_v2(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                # tenant_id is required
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }

                # audit_events is required, as a list
                try:
                    audit_events = resp_dict["audit_events"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "audit_events is required",
                        },
                        "status": 500,
                    }

                if not isinstance(audit_events, list):

                    try:
                        audit_events = json.loads(audit_events)

                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"audit_events should be a list, received type: {type(audit_events)}, content={audit_events}, we have tried to load it as a list but we failed with exception={str(e)}",
                            },
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows registering TrackMe audit events.",
                "resource_desc": "Register new audit events",
                "resource_spl_example": '| trackme url="/services/trackme/v2/audit/audit_events_v2" mode="post", body="{\'tenant_id\': '
                + "'mytenant', 'audit_events': '[<events list>]'"
                + "'object_attrs': '<object attributes>', 'result': '<operation results>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "audit_events": "A list of audit events to be registered (see below)",
                        "audit_events_fields": [
                            {
                                "tenant_id": "REQUIRED. The tenant identifier",
                                "object": "The object name related to the audit event",
                                "object_category": "The category related to the object",
                                "object_state": "The object state",
                                "object_previous_state": "The object previous state",
                                "latest_flip_time": "The latest flip time",
                                "latest_flip_state": "The latest flip state",
                                "anomaly_reason": "The reason for the anomaly, defaults to 'none' if not specified",
                                "result": "The result of the change operation, either a human readable message or the server technical answer",
                                "comment": 'A comment provided by the user or the automation system for that change, if not provided defaults to "No comment for update."',
                            }
                        ],
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Register the new audit event using libs

        # get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackme_audit_default_idx = trackme_conf["trackme_conf"]["index_settings"][
            "trackme_audit_idx"
        ]

        # Get the target index for the tenant_id
        if tenant_id != "all":
            tenant_idx = trackme_idx_for_tenant(
                request_info.system_authtoken, request_info.server_rest_uri, tenant_id
            )
            tenant_audit_idx = tenant_idx["trackme_audit_idx"]

        else:
            tenant_audit_idx = trackme_audit_default_idx

        # check audit_events and verify for the presence of the field tenant_id, if not present add it
        # fix Issue#873
        for event in audit_events:
            if "tenant_id" not in event:
                event["tenant_id"] = tenant_id

        # call the function trackme_audit_gen
        try:
            trackme_audit_gen(tenant_audit_idx, audit_events)

            return {
                "payload": {
                    "action": "success",
                    "result": f"Audit events were processed successfully, {len(audit_events)} events were registered.",
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "response": "audit event has failed",
                "exception": str(e),
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Register multiple handler events at once
    def post_handler_events(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                # tenant_id is required
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }

                # source, optional and defaults to trackme:api if not submitted
                try:
                    source = resp_dict["source"]
                except Exception as e:
                    source = "trackme:api"

                # sourcetype, optional and defaults to trackme:state if not submitted
                try:
                    sourcetype = resp_dict["sourcetype"]
                except Exception as e:
                    sourcetype = "trackme:handler"

                # handler_events is required, as a list
                try:
                    handler_events = resp_dict["handler_events"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "handler_events is required",
                        },
                        "status": 500,
                    }

                if not isinstance(handler_events, list):

                    try:
                        handler_events = json.loads(handler_events)

                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"handler_events should be a list, received type: {type(handler_events)}, content={handler_events}, we have tried to load it as a list but we failed with exception={str(e)}",
                            },
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows registering multiple handler events at once.",
                "resource_desc": "Index multiple handler events",
                "resource_spl_example": '| trackme url="/services/trackme/v2/audit/handler_events" mode="post", body="{\'tenant_id\': '
                + "'mytenant', 'handler_events': '[<events list>]', 'source': 'trackme:api', 'sourcetype': 'trackme:handler'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "handler_events": "A list of handler events to be registered",
                        "source": "The source of the handler event, defaults to trackme:api if not specified",
                        "sourcetype": "The sourcetype of the handler event, defaults to trackme:handler if not specified",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Register the new audit event using libs

        # get TrackMe conf
        trackme_conf = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackme_summary_default_idx = trackme_conf["trackme_conf"]["index_settings"][
            "trackme_summary_idx"
        ]

        # Get the target index for the tenant_id
        if tenant_id != "all":
            tenant_idx = trackme_idx_for_tenant(
                request_info.system_authtoken, request_info.server_rest_uri, tenant_id
            )
            tenant_summary_idx = tenant_idx["trackme_summary_idx"]

        else:
            tenant_summary_idx = trackme_summary_default_idx

        # check audit_events and verify for the presence of the field tenant_id, if not present add it
        # fix Issue#873
        for event in handler_events:
            if "tenant_id" not in event:
                event["tenant_id"] = tenant_id

        # call the function trackme_handler_events_gen
        try:
            trackme_handler_events_gen(
                tenant_summary_idx, handler_events, source, sourcetype
            )

            return {
                "payload": {
                    "action": "success",
                    "result": f"Handler events were processed successfully, {len(handler_events)} events were registered.",
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "response": "handler event has failed",
                "exception": str(e),
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Register a flip event
    def post_flip_event(self, request_info, **kwargs):
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
                object_name = resp_dict["object"]
                object_category = resp_dict["object_category"]
                object_state = resp_dict["object_state"]
                object_previous_state = resp_dict["object_previous_state"]
                latest_flip_time = resp_dict["latest_flip_time"]
                latest_flip_state = resp_dict["latest_flip_state"]
                anomaly_reason = resp_dict.get("anomaly_reason", "none")
                result = resp_dict["result"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows registering a TrackMe flipping event.",
                "resource_desc": "Register a flipping event",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/flip_event" mode="post", body="{\'tenant_id\': '
                + "'mytenant', 'object': 'network:pan:traffic', 'object_category': 'splk-dsm', "
                + "'object_state': 'red', 'object_previous_state': 'green', 'latest_flip_time': '1689613080', 'latest_flip_state': 'red', 'result': 'my message'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object": "The object name related to the audit event",
                        "object_category": "The category related to the object",
                        "object_state": "The object state",
                        "object_previous_state": "The object previous state",
                        "latest_flip_time": "The latest flip time",
                        "latest_flip_state": "The latest flip state",
                        "anomaly_reason": "The reason for the anomaly, defaults to 'none' if not specified",
                        "result": "The result of the change operation, either a human readable message or the server technical answer",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # TrackMe reqinfo
        reqinfo_trackme = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        trackmeconf = reqinfo_trackme["trackme_conf"]["index_settings"]

        # get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # Register the new audit event using libs
        try:
            # Define Meta
            splunk_sourcetype = "trackme:flip"
            splunk_source = "flip_state_change_tracking"
            splunk_host = request_info.server_servername

            audit_event = {
                "_time": str(time.time()),
                "timeStr": str(datetime.datetime.now()),
                "tenant_id": tenant_id,
                "object": object_name,
                "object_category": object_category,
                "object_state": object_state,
                "object_previous_state": object_previous_state,
                "latest_flip_time": latest_flip_time,
                "latest_flip_state": latest_flip_state,
                "anomaly_reason": anomaly_reason,
                "result": result,
            }

            # calculate the event_id as the sha-256 sum of the audit_event
            event_id = hashlib.sha256(json.dumps(audit_event).encode()).hexdigest()
            audit_event["event_id"] = event_id
            audit_event = json.dumps(audit_event)

            # get the target index
            tenant_indexes = trackme_idx_for_tenant(
                request_info.system_authtoken, request_info.server_rest_uri, tenant_id
            )

            # index the audit record
            target = service.indexes[tenant_indexes["trackme_summary_idx"]]
            target.submit(
                event=str(audit_event),
                source=str(splunk_source),
                sourcetype=str(splunk_sourcetype),
                host=str(splunk_host),
            )

            return {
                "payload": {
                    "action": "success",
                    "result": "The flipping record was registered successfully",
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "response": "flipping event has failed",
                "exception": str(e),
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Register a state event
    def post_state_event(self, request_info, **kwargs):
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict.get("tenant_id", None)
                if not tenant_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "tenant_id is required",
                        },
                        "status": 500,
                    }
                index = resp_dict.get("index", "trackme_summary")
                sourcetype = resp_dict.get("sourcetype", "trackme:state")
                source = resp_dict.get("source", "trackme:api")
                record = resp_dict.get("record", None)
                if not record:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "record is required",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint allows registering a TrackMe state event.",
                "resource_desc": "Register a state event",
                "resource_spl_example": '| trackme url="/services/trackme/v2/vtenants/state_event" mode="post", body="{\'tenant_id\': '
                + "'mytenant', 'source': 'mysource', 'record': 'myrecord'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "index": "The target index. If not specified, defaults to trackme_summary",
                        "sourcetype": "The value for the sourcetype Splunk Metadata. Defaults to trackme:state if not specified",
                        "source": "The value for the source Splunk Metadata. Defaults to trackme:api if not specified",
                        "record": "The record to be indexed, can be submitted as a string or a JSON object",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # add event_id and convert
        if isinstance(record, dict):
            # calculate the event_id as the sha-256 sum of the audit_event
            event_id = hashlib.sha256(json.dumps(record).encode()).hexdigest()
            record["event_id"] = event_id
            record = json.dumps(record)

        # index the audit record
        target = service.indexes[index]
        try:
            target.submit(
                event=record,
                source=source,
                sourcetype=sourcetype,
                host=request_info.server_servername,
            )

            return {
                "payload": {
                    "action": "success",
                    "result": "The state record was registered successfully",
                },
                "status": 200,
            }
        except Exception as e:
            response = {
                "action": "failure",
                "response": "state event has failed",
                "exception": str(e),
            }
            logger.error(json.dumps(response, indent=2))
            return {
                "payload": response,
                "status": 500,
            }
