#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_describe.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os, sys
import json
import time
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.describe", "trackme_rest_api_describe.log"
)

# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import get_splunkd_timeout, trackme_getloglevel, trackme_parse_describe_flag, trackme_reqinfo

# import the in-process decision-maker engine (used to evaluate entity state
# without an HTTP loopback into load_component_data — see
# ai-context/backend/decision-maker-engine.md).
from trackme_libs_decisionmaker_engine import DecisionMakerEngine

# import describe libs
from trackme_libs_describe import (
    build_entity_description,
    build_entities_summary,
    get_anonymize_setting,
    get_anonymize_index_setting,
    ENTITY_TYPE_MAP,
)

# import Virtual Tenants describe libs
from trackme_libs_describe_vtenants import build_vtenants_description

# import Tenant Home describe libs
from trackme_libs_describe_tenant_home import build_tenant_home_description

# import additional describe libs for AI assistant contexts
from trackme_libs_describe_rest_api_reference import build_rest_api_reference_description
from trackme_libs_describe_backup_restore import build_backup_restore_description
from trackme_libs_describe_maintenance import (
    build_maintenance_mode_description,
    build_maintenance_kdb_description,
    build_bank_holidays_description,
)
from trackme_libs_describe_license import build_license_description

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerDescribe_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerDescribe_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_describe(self, request_info, **kwargs):
        response = {
            "resource_group_name": "describe",
            "resource_group_desc": "Entity description endpoints for AI agent integration. These endpoints provide comprehensive, structured descriptions of TrackMe entities including identity, health state, configuration, metrics, and investigation searches.",
        }

        return {"payload": response, "status": 200}

    # Describe a single entity
    def post_entity(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/entity" mode="post" body="{'tenant_id': 'mytenant', 'object_category': 'splk-dsm', 'object': 'myindex:mysourcetype'}"
        """

        # init
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
                            "action": "failure",
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }
                try:
                    object_category = resp_dict["object_category"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the object_category is required",
                        },
                        "status": 500,
                    }

                # Validate object_category
                if object_category not in ENTITY_TYPE_MAP:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'invalid object_category="{object_category}", valid values are: {", ".join(ENTITY_TYPE_MAP.keys())}',
                        },
                        "status": 500,
                    }

                # object or object_id must be provided, but not both
                object_value = resp_dict.get("object")
                object_id = resp_dict.get("object_id")

                if object_value and object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "only object or object_id can be specified, not both",
                        },
                        "status": 500,
                    }

                if not object_value and not object_id:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "either object or object_id must be specified",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a comprehensive, AI-consumable description of a TrackMe entity. It requires a POST call with the following information:",
                "resource_desc": "Return a structured description of a TrackMe entity including identity, health state, configuration, metrics summary, and investigation searches.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/entity" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_category\': \'splk-dsm\', \'object\': \'myindex:mysourcetype\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_category": f"The entity type. Valid values: {', '.join(ENTITY_TYPE_MAP.keys())}",
                        "object": "The entity identifier. You can specify either the object or the object_id, but not both",
                        "object_id": "The entity key identifier. You can specify either the object or the object_id, but not both",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        ))

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=splunkd_timeout,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get the entity type configuration
        type_config = ENTITY_TYPE_MAP[object_category]
        component = type_config["short"]

        # Get the realtime decision-maker view of the entity using the
        # in-process DecisionMakerEngine. Same library code as the REST
        # handler's load_component_data (set_*_status / scoring helpers /
        # threshold lookups) but no HTTP loopback or JSON serialization layer.
        try:
            engine = DecisionMakerEngine(
                session_key=request_info.session_key,
                splunkd_uri=request_info.server_rest_uri,
                tenant_id=tenant_id,
                component=component,
                system_authtoken=request_info.system_authtoken,
                splunkd_port=request_info.server_rest_port,
                logger=logger,
            )
            engine.load()

            # Match the previous behaviour: object_value (filter_object)
            # takes precedence over object_id (filter_key).
            if object_value:
                kvrecord = engine.evaluate_object_full(object_value, lookup_field="object")
            elif object_id:
                kvrecord = engine.evaluate_object_full(object_id, lookup_field="_key")
            else:
                kvrecord = None

            if kvrecord is None:
                identifier = object_value or object_id
                return {
                    "payload": {
                        "action": "failure",
                        "response": f'the entity with identifier="{identifier}" was not found for tenant_id="{tenant_id}", component="{component}"',
                    },
                    "status": 404,
                }

        except Exception as e:
            identifier = object_value or object_id
            error_msg = f'failed to retrieve entity from decision maker for identifier="{identifier}", tenant_id="{tenant_id}", component="{component}", exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "action": "failure",
                    "response": error_msg,
                },
                "status": 500,
            }

        # Read anonymization settings
        anonymize = get_anonymize_setting(service)
        anonymize_indexes = get_anonymize_index_setting(service)

        # Build the entity description
        try:
            response = build_entity_description(
                request_info, service, tenant_id, object_category, kvrecord,
                anonymize=anonymize, anonymize_indexes=anonymize_indexes,
            )
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered while building the entity description, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Entities summary
    def post_entities_summary(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/entities_summary" mode="post" body="{'tenant_id': 'mytenant', 'object_category': 'splk-dsm'}"
        """

        # init
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
                            "action": "failure",
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }
                try:
                    object_category = resp_dict["object_category"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the object_category is required",
                        },
                        "status": 500,
                    }

                # Validate object_category
                if object_category not in ENTITY_TYPE_MAP:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'invalid object_category="{object_category}", valid values are: {", ".join(ENTITY_TYPE_MAP.keys())}',
                        },
                        "status": 500,
                    }

                # Optional filters
                filter_object_state = resp_dict.get("filter_object_state")
                filter_priority = resp_dict.get("filter_priority")
                filter_monitored_state = resp_dict.get("filter_monitored_state")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a lightweight summary of entities for a given tenant and entity type. It requires a POST call with the following information:",
                "resource_desc": "Return a summary listing of TrackMe entities with state counts and per-entity status for AI agent discovery.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/entities_summary" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_category\': \'splk-dsm\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_category": f"The entity type. Valid values: {', '.join(ENTITY_TYPE_MAP.keys())}",
                        "filter_object_state": "(optional) Filter by object state: green, red, orange, blue",
                        "filter_priority": "(optional) Filter by priority: low, medium, high, critical",
                        "filter_monitored_state": "(optional) Filter by monitored state: enabled, disabled",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        ))

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=splunkd_timeout,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get the entity type configuration
        type_config = ENTITY_TYPE_MAP[object_category]
        component = type_config["short"]

        # Get the realtime decision-maker view of every entity using the
        # in-process DecisionMakerEngine. Same library code as the REST
        # handler's load_component_data (set_*_status / scoring helpers /
        # threshold lookups) but no HTTP loopback or JSON serialization layer.
        # evaluate_all() also applies the per-component blocklist filter so
        # the returned record set matches what load_component_data would have
        # returned with no filter parameters.
        try:
            engine = DecisionMakerEngine(
                session_key=request_info.session_key,
                splunkd_uri=request_info.server_rest_uri,
                tenant_id=tenant_id,
                component=component,
                system_authtoken=request_info.system_authtoken,
                splunkd_port=request_info.server_rest_port,
                logger=logger,
            )
            engine.load()
            records = engine.evaluate_all()

        except Exception as e:
            error_msg = f'failed to retrieve entities from decision maker for tenant_id="{tenant_id}", component="{component}", exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {
                    "action": "failure",
                    "response": error_msg,
                },
                "status": 500,
            }

        # Apply optional filters client-side on the realtime data
        if filter_object_state:
            records = [r for r in records if r.get("object_state") == filter_object_state]
        if filter_priority:
            records = [r for r in records if r.get("priority") == filter_priority]
        if filter_monitored_state:
            records = [r for r in records if r.get("monitored_state") == filter_monitored_state]

        # Read anonymization settings
        anonymize = get_anonymize_setting(service)
        anonymize_indexes = get_anonymize_index_setting(service)

        # Build the summary
        try:
            response = build_entities_summary(
                records, object_category, tenant_id,
                anonymize=anonymize, anonymize_indexes=anonymize_indexes,
            )
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered while building the entities summary, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Virtual Tenants environment for AI consumption
    def post_vtenants(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/vtenants" mode="post"
        """

        # init
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            # No body submitted, describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a comprehensive, AI-consumable description of all Virtual Tenants accessible to the current user. No parameters are required.",
                "resource_desc": "Return a structured description of the Virtual Tenants environment including tenant configurations, entity counts, alert counts, RBAC, and a knowledge reference for AI assistance.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/vtenants" mode="post"',
                "options": [
                    {
                        "note": "No parameters are required. The endpoint returns all tenants accessible to the current user based on RBAC.",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # System-level service for KV store access
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

        # Build the Virtual Tenants description
        try:
            response = build_vtenants_description(service, request_info)
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered while building the Virtual Tenants description, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Tenant Home environment for AI consumption
    def post_tenant_home(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/tenant_home" mode="post" body="{'tenant_id': 'mytenant'}"
        """

        # init
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
                            "action": "failure",
                            "response": "the tenant_id is required",
                        },
                        "status": 500,
                    }
        else:
            # No body submitted, describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a comprehensive, AI-consumable description of a single tenant for the Tenant Home AI assistant. It requires a POST call with the tenant_id.",
                "resource_desc": "Return a structured description of a specific tenant including identity, components, configuration, feature counts, alerting summary, health distribution, and knowledge reference.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/tenant_home" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # System-level service for KV store access
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

        # Build the Tenant Home description
        try:
            response = build_tenant_home_description(service, request_info, tenant_id)
            return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered while building the Tenant Home description, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe REST API Reference for AI consumption
    def post_rest_api_reference(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/rest_api_reference" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured REST API reference for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return a knowledge reference of the TrackMe REST API including resource groups, authentication, and usage patterns.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/rest_api_reference" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_rest_api_reference_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the REST API Reference description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Backup & Restore for AI consumption
    def post_backup_restore(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/backup_restore" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured description of the Backup & Restore state for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return backup records and knowledge reference for the AI assistant.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/backup_restore" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_backup_restore_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the Backup & Restore description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Maintenance Mode for AI consumption
    def post_maintenance_mode(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/maintenance_mode" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured description of the Maintenance Mode state for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return maintenance mode status and knowledge reference for the AI assistant.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/maintenance_mode" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_maintenance_mode_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the Maintenance Mode description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Maintenance KDB for AI consumption
    def post_maintenance_kdb(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/maintenance_kdb" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured description of the Maintenance Knowledge Database for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return maintenance KDB records and knowledge reference for the AI assistant.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/maintenance_kdb" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_maintenance_kdb_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the Maintenance KDB description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe Bank Holidays for AI consumption
    def post_bank_holidays(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/bank_holidays" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured description of the Bank Holidays configuration for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return bank holidays records and knowledge reference for the AI assistant.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/bank_holidays" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_bank_holidays_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the Bank Holidays description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Describe License Management for AI consumption
    def post_license(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/describe/license" mode="post"
        """

        describe = False
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns a structured description of the License Management state for AI assistant consumption. No parameters are required.",
                "resource_desc": "Return license status and knowledge reference for the AI assistant.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/describe/license" mode="post"',
                "options": [{"note": "No parameters are required."}],
            }
            return {"payload": response, "status": 200}

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody", app="trackme", port=splunkd_port,
            token=request_info.system_authtoken, timeout=600,
        )
        loglevel = trackme_getloglevel(request_info.system_authtoken, request_info.server_rest_port)
        logger.setLevel(loglevel)

        try:
            response = build_license_description(service, request_info)
            return {"payload": response, "status": 200}
        except Exception as e:
            response = {"action": "failure", "response": f'an exception was encountered while building the License description, exception="{str(e)}"'}
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
