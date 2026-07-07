#!/usr/bin/env python
# coding=utf-8

"""
TrackMe REST Handler — AI ML Outlier Advisor

Endpoints:
    POST /trackme/v2/ai_ml_advisor/ml_advisor         — Start an ML advisor agent analysis
    GET  /trackme/v2/ai_ml_advisor/ml_advisor_status  — Poll agent job status
    DELETE /trackme/v2/ai_ml_advisor/ml_advisor_cancel — Cancel a running agent job

TEMPORARY: This handler is part of the AI Agent SDK beta integration.
"""

__name__ = "trackme_rest_handler_ai_ml_advisor.py"
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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.ai.ml_advisor", "trackme_rest_api_ai_advisor_mloutliers.log")

# import rest handler
import trackme_rest_handler

# import trackme libs
import splunklib.client as client

from trackme_libs import trackme_parse_describe_flag

from trackme_libs_ai_agents import (
    start_ml_advisor_async,
    get_agent_job_status,
    _update_agent_job,
    _release_agent_slot,
    _KV_COLLECTION_AGENT_JOBS,
)


class TrackMeHandlerAiMlAdvisor_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiMlAdvisor_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_ai_ml_advisor(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ai_ml_advisor",
            "resource_group_desc": "AI ML Outlier Advisor agent endpoints. These endpoints enable AI-powered analysis, recommendation, and auto-tuning of ML outlier detection models.",
        }
        return {"payload": response, "status": 200}

    # -----------------------------------------------------------------
    # POST /trackme/v2/ai_ml_advisor/ml_advisor — Start analysis
    # -----------------------------------------------------------------
    def post_ml_advisor(self, request_info, **kwargs):
        """
        Start an ML Outlier Advisor agent analysis for an entity.

        POST body (JSON):
            tenant_id (required): Tenant identifier
            component (required): Component type — dsm, dhm, flx, fqm, wlk
            object (optional): Entity name. Specify object or object_id, but not both.
            object_id (optional): Entity _key hash. Specify object or object_id, but not both.
            mode (optional): "inspect" (default) or "act"
            provider_name (optional): AI provider name (uses first configured if omitted)

        Returns:
            {"job_id": "uuid", "status": "running"}
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Start an ML Outlier Advisor agent analysis. The "
                        "advisor inspects an entity's native outlier "
                        "models (DensityFunction), detection state, and "
                        "anomaly history, then proposes per-model "
                        "remediations: confidence-level shifts, "
                        "seasonality adjustments, period exclusions, "
                        "or model resets. ``inspect`` mode is read-only "
                        "with recommendations; ``act`` mode applies "
                        "model changes automatically. Supported "
                        "components: typically ``dsm`` / ``flx`` (where "
                        "ML outlier detection is recommended)."
                    ),
                    "resource_desc": (
                        "Start an asynchronous ML Outlier Advisor "
                        "agent run for one entity"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_ml_advisor/ml_advisor" '
                        'mode="post" body="{\'tenant_id\': \'mytenant\', '
                        '\'component\': \'dsm\', \'object_id\': \'<entity_key>\', '
                        '\'mode\': \'inspect\'}"'
                    ),
                    "options": [
                        {
                            "tenant_id": (
                                "Required. The virtual tenant the entity "
                                "belongs to."
                            ),
                            "component": (
                                "Required. Component family the entity "
                                "belongs to (e.g. ``dsm``, ``flx``)."
                            ),
                            "object": (
                                "Conditional. The entity's human-readable "
                                "name. Provide EITHER ``object`` OR "
                                "``object_id``, never both."
                            ),
                            "object_id": (
                                "Conditional. The entity's KV ``_key`` "
                                "hash. Provide EITHER ``object`` OR "
                                "``object_id``, never both. Preferred "
                                "when available."
                            ),
                            "mode": (
                                "Optional. ``inspect`` (default, "
                                "read-only with recommendations) or "
                                "``act`` (apply model changes "
                                "automatically)."
                            ),
                            "provider_name": (
                                "Optional. AI provider stanza name. "
                                "Defaults to the first configured provider."
                            ),
                            "user_context": (
                                "Optional. Free-text additional "
                                "instructions from the operator (e.g. "
                                "\"do not retrain models\")."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        # Parse request body
        try:
            body = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except (json.JSONDecodeError, ValueError) as e:
            return {
                "payload": {"error": f"Invalid JSON in request body: {e}"},
                "status": 400,
            }

        # Validate required parameters
        tenant_id = body.get("tenant_id")
        component = body.get("component")
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
                "payload": {
                    "error": "Either object or object_id must be provided"
                },
                "status": 400,
            }

        if object_value and object_id:
            return {
                "payload": {
                    "error": "Only object or object_id can be specified, not both"
                },
                "status": 400,
            }

        # Validate component
        valid_components = {"dsm", "dhm", "flx", "fqm", "wlk"}
        if component not in valid_components:
            return {
                "payload": {
                    "error": f"Invalid component '{component}'. Must be one of: {sorted(valid_components)}"
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

        # Audit attribution — distinguishes manual UI launches from
        # AI-Assistant-triggered launches (the chat bridge) and from future
        # automated runs. The chat bridge passes ``launched_by="ai_assistant"``
        # plus a ``chat_session_id`` so the resulting advisor run can be
        # traced back to the conversation that authorised it. See
        # ``ai-context/integrations/ai-assistant-ai-advisor-bridge.md``.
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

        # Create services
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

        # Check if AI features are enabled (server-side enforcement)
        try:
            trackme_settings = system_service.confs["trackme_settings"]
            for stanza in trackme_settings:
                if stanza.name == "trackme_general":
                    if stanza.content.get("enable_ai_assistant", "1") == "0":
                        return {
                            "payload": {
                                "error": "AI features are disabled by the administrator. "
                                "Enable AI features in the TrackMe configuration page (General > Artificial Intelligence)."
                            },
                            "status": 403,
                        }
                    break
        except Exception as e:
            logger.warning(f"Could not check AI feature toggle: {e}")

        # Resolve object/object_id: we need both the _key (object_id) and
        # entity name (object_name) for downstream use.
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
            result = start_ml_advisor_async(
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
                f'function=post_ml_advisor, tenant_id="{tenant_id}", '
                f'component="{component}", object_id="{object_id}", '
                f'object_name="{object_name}", '
                f'mode="{mode}", job_id="{result.get("job_id")}"'
            )

            return {"payload": result, "status": 200}

        except ValueError as e:
            # AI not configured
            return {"payload": {"error": str(e)}, "status": 400}
        except RuntimeError as e:
            # Concurrency limit
            return {"payload": {"error": str(e)}, "status": 429}
        except Exception as e:
            logger.error(f"ML Advisor start failed: {e}", exc_info=True)
            return {"payload": {"error": f"Failed to start ML advisor: {e}"}, "status": 500}

    # -----------------------------------------------------------------
    # GET /trackme/v2/ai_ml_advisor/ml_advisor_status — Poll job status
    # -----------------------------------------------------------------
    def get_ml_advisor_status(self, request_info, **kwargs):
        """
        Get the status of an ML Advisor agent job.

        Query parameters:
            job_id (required): The job identifier returned by POST /ml_advisor

        Returns:
            {
                "status": "running" | "complete" | "error" | "cancelled",
                "result": { MLAdvisorResult } | null,
                "error": "..." | ""
            }
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Poll the status of an ML Outlier Advisor agent "
                        "job. Returns ``running`` / ``complete`` / "
                        "``error`` / ``cancelled``, the live progress "
                        "feed, and (on completion) the structured "
                        "``MLAdvisorResult`` payload."
                    ),
                    "resource_desc": (
                        "Poll an ML Advisor agent job's status, "
                        "progress, and result"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_ml_advisor/ml_advisor_status" '
                        'mode="get" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID returned "
                                "by ``post_ml_advisor``."
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
    # DELETE /trackme/v2/ai_ml_advisor/ml_advisor_cancel — Cancel job
    # -----------------------------------------------------------------
    def delete_ml_advisor_cancel(self, request_info, **kwargs):
        """
        Cancel a running ML Advisor agent job.

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
                        "Cancel a running ML Outlier Advisor agent job. "
                        "Best-effort — tool calls in flight may still "
                        "complete, but the job record is marked "
                        "``cancelled`` immediately so the UI stops "
                        "polling for a meaningful result."
                    ),
                    "resource_desc": (
                        "Cancel a running ML Advisor agent job"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_ml_advisor/ml_advisor_cancel" '
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

        # Check current status
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

        # Cancel the job
        _update_agent_job(system_service, job_id, "cancelled", error="Cancelled by user")
        _release_agent_slot(job_id)

        logger.info(f'function=delete_ml_advisor_cancel, job_id="{job_id}"')

        return {"payload": {"status": "cancelled"}, "status": 200}
