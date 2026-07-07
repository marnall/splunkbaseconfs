#!/usr/bin/env python
# coding=utf-8

"""
TrackMe REST Handler — AI Component Health Advisor

Endpoints:
    POST   /trackme/v2/ai_component_health/health_advisor         — Start agent analysis
    GET    /trackme/v2/ai_component_health/health_advisor_status  — Poll agent job status
    DELETE /trackme/v2/ai_component_health/health_advisor_cancel  — Cancel running job
"""

__name__ = "trackme_rest_handler_ai_component_health.py"
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

splunkhome = os.environ["SPLUNK_HOME"]

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import import_declare_test

from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.ai.component_health", "trackme_rest_api_ai_advisor_component_health.log")

import trackme_rest_handler

import splunklib.client as client

from trackme_libs import trackme_parse_describe_flag

from trackme_libs_ai_agents import (
    get_agent_job_status,
    _update_agent_job,
    _release_agent_slot,
)

from trackme_libs_ai_component_health import (
    start_component_health_advisor_async,
)


class TrackMeHandlerAiComponentHealth_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiComponentHealth_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_ai_component_health(self, request_info, **kwargs):
        return {
            "payload": {
                "resource_group_name": "ai_component_health",
                "resource_group_desc": "AI Component Health Advisor endpoints for WLK and MHM entities.",
            },
            "status": 200,
        }

    # -----------------------------------------------------------------
    # POST /trackme/v2/ai_component_health/health_advisor — Start analysis
    # -----------------------------------------------------------------
    def post_health_advisor(self, request_info, **kwargs):
        """
        Start a Component Health Advisor agent analysis for a WLK or MHM entity.

        POST body (JSON):
            tenant_id (required): Tenant identifier
            component (required): Component type — wlk or mhm
            object (optional): Entity name. Specify object or object_id, but not both.
            object_id (optional): Entity _key hash. Specify object or object_id, but not both.
            mode (optional): "inspect" (default) or "act"
            provider_name (optional): AI provider name (uses first configured if omitted)
            user_context (optional): Free-text instructions to guide the agent

        Returns:
            {"job_id": "uuid", "status": "running"}
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Start a Component Health Advisor agent analysis "
                        "for a WLK (workload knowledge) or MHM (metric host "
                        "monitoring) entity. The advisor inspects component "
                        "health, identifies misconfigurations, and proposes "
                        "remediations. ``inspect`` mode is read-only; "
                        "``act`` mode applies changes automatically. "
                        "Supported components: ``wlk``, ``mhm``."
                    ),
                    "resource_desc": (
                        "Start an asynchronous Component Health Advisor "
                        "agent run for a WLK or MHM entity"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_component_health/health_advisor" '
                        'mode="post" body="{\'tenant_id\': \'mytenant\', '
                        '\'component\': \'wlk\', \'object_id\': \'<entity_key>\', '
                        '\'mode\': \'inspect\'}"'
                    ),
                    "options": [
                        {
                            "tenant_id": (
                                "Required. The virtual tenant the entity "
                                "belongs to."
                            ),
                            "component": (
                                "Required. Component family — one of "
                                "``wlk`` or ``mhm``."
                            ),
                            "object": (
                                "Conditional. The entity's human-readable "
                                "name. Provide EITHER ``object`` OR "
                                "``object_id``, never both."
                            ),
                            "object_id": (
                                "Conditional. The entity's KV ``_key`` "
                                "hash. Provide EITHER ``object`` OR "
                                "``object_id``, never both. ``object_id`` "
                                "is preferred when available — it survives "
                                "URL encoding cleanly."
                            ),
                            "mode": (
                                "Optional. ``inspect`` (default, read-only "
                                "analysis with recommendations) or ``act`` "
                                "(analysis + apply changes automatically)."
                            ),
                            "provider_name": (
                                "Optional. AI provider stanza name. "
                                "Defaults to the first configured provider."
                            ),
                            "user_context": (
                                "Optional. Free-text additional "
                                "instructions from the operator (e.g. "
                                "\"do not propose schema changes\")."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        try:
            body = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "payload": {"error": f"Invalid JSON in request body: {e}"},
                "status": 400,
            }

        tenant_id = body.get("tenant_id")
        component = body.get("component")
        # Accept either `object` (entity name) or `object_id` (_key hash); the
        # other half is resolved from the component KV collection below.  This
        # mirrors the ML / Feed Lifecycle / FLX Threshold handlers so all four
        # advisor endpoints have the same input contract.
        object_value = body.get("object")
        object_id = body.get("object_id")

        if not tenant_id or not component:
            return {
                "payload": {
                    "error": "Missing required parameters. Required: tenant_id, component, and either object or object_id"
                },
                "status": 400,
            }

        if not object_value and not object_id:
            return {
                "payload": {"error": "Either object or object_id must be provided"},
                "status": 400,
            }

        if object_value and object_id:
            return {
                "payload": {"error": "Only object or object_id can be specified, not both"},
                "status": 400,
            }

        valid_components = {"wlk", "mhm"}
        if component not in valid_components:
            return {
                "payload": {
                    "error": f"Invalid component '{component}'. Component Health Advisor supports: {sorted(valid_components)}"
                },
                "status": 400,
            }

        mode = body.get("mode", "inspect")
        valid_modes = {"inspect", "act"}
        if mode not in valid_modes:
            return {
                "payload": {
                    "error": f"Invalid mode '{mode}'. Must be one of: {sorted(valid_modes)}"
                },
                "status": 400,
            }

        provider_name = body.get("provider_name")
        user_context = body.get("user_context")

        # Audit attribution — see ml_advisor handler for the canonical doc;
        # mirrored across all 5 advisor REST handlers (Phase 2 of the
        # AI Assistant ↔ AI Advisor bridge).
        launched_by = body.get("launched_by", "ui") or "ui"
        valid_launched_by = {"ui", "ai_assistant", "automation"}
        if launched_by not in valid_launched_by:
            return {
                "payload": {
                    "error": (
                        f"Invalid launched_by '{launched_by}'. Must be one of: "
                        f"{sorted(valid_launched_by)}"
                    )
                },
                "status": 400,
            }
        chat_session_id = body.get("chat_session_id") or ""

        try:
            system_service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )

            user_service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.session_key,
                timeout=600,
            )
        except Exception as e:
            return {
                "payload": {"error": f"Failed to connect to Splunk: {e}"},
                "status": 500,
            }

        # Check AI features enabled
        try:
            trackme_settings = system_service.confs["trackme_settings"]
            for stanza in trackme_settings:
                if stanza.name == "trackme_general":
                    if stanza.content.get("enable_ai_assistant", "1") == "0":
                        return {
                            "payload": {
                                "error": (
                                    "AI features are disabled by the administrator. "
                                    "Enable AI features in the TrackMe configuration page "
                                    "(General > Artificial Intelligence)."
                                )
                            },
                            "status": 403,
                        }
                    break
        except Exception as e:
            logger.warning(f"Could not check AI feature toggle: {e}")

        # Resolve object/object_id: downstream helpers need both the _key
        # (object_id) and the entity display name (object_name).  Same
        # pattern as the ML / Feed Lifecycle / FLX Threshold handlers.
        try:
            collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            collection = system_service.kvstore[collection_name]

            if object_value:
                # Look up by entity name to get the _key
                records = collection.data.query(
                    query=json.dumps({"object": object_value})
                )
                if not records:
                    return {
                        "payload": {"error": f'Entity with object="{object_value}" not found'},
                        "status": 404,
                    }
                object_id = records[0].get("_key")
                object_name = object_value
            else:
                # Look up by _key to get the entity name
                records = collection.data.query(
                    query=json.dumps({"_key": object_id})
                )
                if not records:
                    return {
                        "payload": {"error": f'Entity with object_id="{object_id}" not found'},
                        "status": 404,
                    }
                object_name = records[0].get("object", "")

        except Exception as e:
            return {
                "payload": {"error": f"Failed to resolve entity: {e}"},
                "status": 500,
            }

        # Start the agent
        try:
            result = start_component_health_advisor_async(
                system_service=system_service,
                user_service=user_service,
                request_info=request_info,
                tenant_id=tenant_id,
                component=component,
                object_id=object_id,
                object_name=object_name,
                mode=mode,
                provider_name=provider_name,
                user_context=user_context,
                launched_by=launched_by,
                chat_session_id=chat_session_id,
            )

            logger.info(
                f'function=post_health_advisor, tenant_id="{tenant_id}", '
                f'component="{component}", object_id="{object_id}", '
                f'object_name="{object_name}", mode="{mode}", job_id="{result.get("job_id")}"'
            )

            return {"payload": result, "status": 200}

        except ValueError as e:
            return {"payload": {"error": str(e)}, "status": 400}
        except RuntimeError as e:
            return {"payload": {"error": str(e)}, "status": 429}
        except Exception as e:
            logger.error(f"Component Health Advisor start failed: {e}", exc_info=True)
            return {"payload": {"error": f"Failed to start Component Health Advisor: {e}"}, "status": 500}

    # -----------------------------------------------------------------
    # GET /trackme/v2/ai_component_health/health_advisor_status
    # -----------------------------------------------------------------
    def get_health_advisor_status(self, request_info, **kwargs):
        """
        Get the status of a Component Health Advisor agent job.

        Query parameters:
            job_id (required): The job identifier returned by POST /health_advisor

        Returns:
            {
                "status": "running" | "complete" | "error" | "cancelled",
                "result": { ComponentHealthAdvisorResult } | null,
                "error": "..." | ""
            }
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Poll the status of a Component Health Advisor "
                        "agent job. Returns ``running`` / ``complete`` / "
                        "``error`` / ``cancelled``, along with the live "
                        "progress feed and (on completion) the structured "
                        "``ComponentHealthAdvisorResult`` payload."
                    ),
                    "resource_desc": (
                        "Poll a Component Health Advisor agent job's "
                        "status, progress, and result"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_component_health/health_advisor_status" '
                        'mode="get" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID returned by "
                                "``post_health_advisor``."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        job_id = kwargs.get("job_id")
        if not job_id:
            return {
                "payload": {"error": "Missing required parameter: job_id"},
                "status": 400,
            }

        try:
            system_service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )
        except Exception as e:
            return {
                "payload": {"error": f"Failed to connect to Splunk: {e}"},
                "status": 500,
            }

        result = get_agent_job_status(system_service, job_id)
        if result is None:
            return {
                "payload": {"error": f"Job not found: {job_id}"},
                "status": 404,
            }

        return {"payload": result, "status": 200}

    # -----------------------------------------------------------------
    # DELETE /trackme/v2/ai_component_health/health_advisor_cancel
    # -----------------------------------------------------------------
    def delete_health_advisor_cancel(self, request_info, **kwargs):
        """
        Cancel a running Component Health Advisor agent job.

        Query parameters:
            job_id (required): The job identifier to cancel

        Returns:
            {"status": "cancelled"} or {"status": "already_done"}
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Cancel a running Component Health Advisor agent "
                        "job. Best-effort — tool calls in flight may still "
                        "complete, but the job record is marked "
                        "``cancelled`` immediately so the UI stops polling "
                        "for a meaningful result."
                    ),
                    "resource_desc": (
                        "Cancel a running Component Health Advisor agent "
                        "job"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_component_health/health_advisor_cancel" '
                        'mode="delete" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID to cancel."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        job_id = kwargs.get("job_id")
        if not job_id:
            return {
                "payload": {"error": "Missing required parameter: job_id"},
                "status": 400,
            }

        try:
            system_service = client.connect(
                owner="nobody",
                app="trackme",
                port=request_info.server_rest_port,
                token=request_info.system_authtoken,
                timeout=600,
            )
        except Exception as e:
            return {
                "payload": {"error": f"Failed to connect to Splunk: {e}"},
                "status": 500,
            }

        current = get_agent_job_status(system_service, job_id)
        if current is None:
            return {
                "payload": {"error": f"Job not found: {job_id}"},
                "status": 404,
            }

        if current["status"] in ("complete", "error", "cancelled"):
            return {
                "payload": {"status": "already_done", "original_status": current["status"]},
                "status": 200,
            }

        _update_agent_job(system_service, job_id, "cancelled", error="Cancelled by user")
        _release_agent_slot(job_id)

        logger.info(f'function=delete_health_advisor_cancel, job_id="{job_id}"')

        return {"payload": {"status": "cancelled"}, "status": 200}
