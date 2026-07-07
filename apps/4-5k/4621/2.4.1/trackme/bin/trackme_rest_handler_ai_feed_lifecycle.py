#!/usr/bin/env python
# coding=utf-8

"""
TrackMe REST Handler — AI Feed Lifecycle Advisor

Endpoints:
    POST   /trackme/v2/ai_feed_lifecycle/lifecycle_advisor         — Start agent analysis
    GET    /trackme/v2/ai_feed_lifecycle/lifecycle_advisor_status  — Poll agent job status
    DELETE /trackme/v2/ai_feed_lifecycle/lifecycle_advisor_cancel  — Cancel running job
"""

__name__ = "trackme_rest_handler_ai_feed_lifecycle.py"
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

logger = setup_logger("trackme.rest.ai.feed_lifecycle", "trackme_rest_api_ai_advisor_feed_lifecycle.log")

import trackme_rest_handler

import splunklib.client as client

from trackme_libs import trackme_parse_describe_flag

from trackme_libs_ai_agents import (
    get_agent_job_status,
    _update_agent_job,
    _release_agent_slot,
)

from trackme_libs_ai_feed_lifecycle import (
    start_feed_lifecycle_advisor_async,
    validate_data_sampling_generate_payload,
)


class TrackMeHandlerAiFeedLifecycle_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiFeedLifecycle_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_ai_feed_lifecycle(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ai_feed_lifecycle",
            "resource_group_desc": (
                "AI Feed Lifecycle Advisor agent endpoints. These endpoints enable AI-powered "
                "analysis and auto-tuning of DSM/DHM entity lifecycle configurations including "
                "thresholds, adaptive delay, variable delay schedules, monitoring state, and priority."
            ),
        }
        return {"payload": response, "status": 200}

    # -----------------------------------------------------------------
    # POST /trackme/v2/ai_feed_lifecycle/lifecycle_advisor — Start analysis
    # -----------------------------------------------------------------
    def post_lifecycle_advisor(self, request_info, **kwargs):
        """
        Start a Feed Lifecycle Advisor agent analysis for a DSM or DHM entity.

        POST body (JSON):
            tenant_id (required): Tenant identifier
            component (required): Component type — dsm or dhm
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
                        "Start a Feed Lifecycle Advisor agent analysis for "
                        "a DSM (data source monitoring) or DHM (data host "
                        "monitoring) entity. The advisor inspects the "
                        "entity's lifecycle configuration (delays, "
                        "retention, monitored state, sampling) and "
                        "proposes adjustments. ``inspect`` mode is "
                        "read-only; ``act`` mode applies changes "
                        "automatically; ``generate_model`` mode runs "
                        "wizard-time from the Data Sampling Create "
                        "Custom Rule UI (no entity required — propose a "
                        "starter regex from a sampled-events payload, "
                        "Phase 3b of issue #1901). Supported components: "
                        "``dsm``, ``dhm`` (generate_model is DSM-only)."
                    ),
                    "resource_desc": (
                        "Start an asynchronous Feed Lifecycle Advisor "
                        "agent run for a DSM or DHM entity (or wizard-"
                        "time model generation)"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor" '
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
                                "Required. Component family — one of "
                                "``dsm`` or ``dhm``. ``generate_model`` "
                                "mode requires ``dsm``."
                            ),
                            "object": (
                                "Conditional. The entity's human-readable "
                                "name. Provide EITHER ``object`` OR "
                                "``object_id`` for ``inspect``/``act`` "
                                "modes, never both. MUST be OMITTED for "
                                "``generate_model``."
                            ),
                            "object_id": (
                                "Conditional. The entity's KV ``_key`` "
                                "hash. Provide EITHER ``object`` OR "
                                "``object_id`` for ``inspect``/``act`` "
                                "modes, never both. Preferred when "
                                "available — survives URL encoding "
                                "cleanly. MUST be OMITTED for "
                                "``generate_model``."
                            ),
                            "mode": (
                                "Optional. ``inspect`` (default, "
                                "read-only), ``act`` (apply changes "
                                "automatically), or ``generate_model`` "
                                "(wizard-time DSM model generation — "
                                "requires ``wizard_payload``, rejects "
                                "``object`` / ``object_id``)."
                            ),
                            "provider_name": (
                                "Optional. AI provider stanza name. "
                                "Defaults to the first configured provider."
                            ),
                            "user_context": (
                                "Optional. Free-text additional "
                                "instructions from the operator. Ignored "
                                "in ``generate_model`` mode (the wizard "
                                "payload is the sole input)."
                            ),
                            "wizard_payload": (
                                "Conditional (REQUIRED for ``mode="
                                "generate_model``, MUST be omitted "
                                "otherwise). JSON object with keys: "
                                "``tenant_id`` (str), ``sourcetype`` "
                                "(str), ``samples`` (list of raw event "
                                "strings — at least 1, at most 100, "
                                "total ≤256 KiB JSON-encoded). See the "
                                "``validate_data_sampling_generate_payload`` "
                                "validator for the full contract."
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
        object_value = body.get("object")
        object_id = body.get("object_id")

        # Mode is parsed FIRST because validation rules diverge per mode:
        # generate_model is wizard-time and rejects object/object_id, while
        # inspect/act require one of them. Phase 3b of issue #1901.
        mode = body.get("mode", "inspect")
        valid_modes = {"inspect", "act", "generate_model"}
        if mode not in valid_modes:
            return {
                "payload": {
                    "error": f"Invalid mode '{mode}'. Must be one of: {sorted(valid_modes)}"
                },
                "status": 400,
            }

        if not tenant_id or not component:
            return {
                "payload": {
                    "error": (
                        "Missing required parameters. Required: tenant_id, component."
                        if mode == "generate_model"
                        else "Missing required parameters. Required: tenant_id, component, and either object or object_id"
                    )
                },
                "status": 400,
            }

        valid_components = {"dsm", "dhm"}
        if component not in valid_components:
            return {
                "payload": {
                    "error": f"Invalid component '{component}'. Feed Lifecycle Advisor supports: {sorted(valid_components)}"
                },
                "status": 400,
            }

        # ``generate_model`` is wizard-time — there is no entity yet, so
        # ``object`` / ``object_id`` are not applicable; the agent's input
        # comes from ``wizard_payload`` instead. Validate strictly to keep
        # the contract clean: reject any attempt to combine the two input
        # shapes. Mirrors the FQM advisor's ``dictionary_generate`` gate.
        wizard_payload = body.get("wizard_payload")

        if mode == "generate_model":
            if object_value or object_id:
                return {
                    "payload": {
                        "error": (
                            "object / object_id must not be provided in "
                            "generate_model mode — there is no entity at "
                            "wizard time. Provide wizard_payload instead."
                        )
                    },
                    "status": 400,
                }
            # generate_model is DSM-only — the wizard exists in the Data
            # Sampling Create Custom Rule modal, which is a DSM feature.
            # Reject DHM wizard requests at the 400-layer. Component
            # check fires BEFORE the payload validator (CodeRabbit PR
            # #1914 — cheaper string check + clearer error message; a
            # DHM caller with a malformed payload should see "DSM-only"
            # not the payload-shape error).
            if component != "dsm":
                return {
                    "payload": {
                        "error": (
                            "generate_model mode is DSM-only — Data "
                            "Sampling is a DSM feature. Component must "
                            "be 'dsm' for this mode."
                        )
                    },
                    "status": 400,
                }
            # Wizard payload is REQUIRED. The validator returns a string
            # error message on any structural issue or None on success.
            # Validation is performed at the 400-layer so a malformed
            # payload never reaches the LLM (saves tokens + audit noise).
            wp_err = validate_data_sampling_generate_payload(wizard_payload)
            if wp_err is not None:
                return {"payload": {"error": wp_err}, "status": 400}
        else:
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

        # Resolve object/object_id — only for inspect/act. ``generate_model``
        # is wizard-time and has no entity, so we skip resolution and pass
        # empty strings down to the agent runner (which branches on mode
        # to construct the wizard-mode initial message from
        # ``wizard_payload`` instead).
        if mode == "generate_model":
            object_id = ""
            object_name = ""
        else:
            try:
                collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
                collection = system_service.kvstore[collection_name]

                if object_value:
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
            result = start_feed_lifecycle_advisor_async(
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
                wizard_payload=wizard_payload,
            )

            logger.info(
                f'function=post_lifecycle_advisor, tenant_id="{tenant_id}", '
                f'component="{component}", object_id="{object_id}", '
                f'object_name="{object_name}", mode="{mode}", job_id="{result.get("job_id")}"'
            )

            return {"payload": result, "status": 200}

        except ValueError as e:
            return {"payload": {"error": str(e)}, "status": 400}
        except RuntimeError as e:
            return {"payload": {"error": str(e)}, "status": 429}
        except Exception as e:
            logger.error(f"Feed Lifecycle Advisor start failed: {e}", exc_info=True)
            return {"payload": {"error": f"Failed to start Feed Lifecycle Advisor: {e}"}, "status": 500}

    # -----------------------------------------------------------------
    # GET /trackme/v2/ai_feed_lifecycle/lifecycle_advisor_status
    # -----------------------------------------------------------------
    def get_lifecycle_advisor_status(self, request_info, **kwargs):
        """
        Get the status of a Feed Lifecycle Advisor agent job.

        Query parameters:
            job_id (required): The job identifier returned by POST /lifecycle_advisor

        Returns:
            {
                "status": "running" | "complete" | "error" | "cancelled",
                "result": { LifecycleAdvisorResult } | null,
                "error": "..." | ""
            }
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Poll the status of a Feed Lifecycle Advisor agent "
                        "job. Returns ``running`` / ``complete`` / "
                        "``error`` / ``cancelled``, the live progress "
                        "feed, and (on completion) the structured "
                        "``FeedLifecycleAdvisorResult`` payload."
                    ),
                    "resource_desc": (
                        "Poll a Feed Lifecycle Advisor agent job's status, "
                        "progress, and result"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor_status" '
                        'mode="get" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID returned by "
                                "``post_lifecycle_advisor``."
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
    # DELETE /trackme/v2/ai_feed_lifecycle/lifecycle_advisor_cancel
    # -----------------------------------------------------------------
    def delete_lifecycle_advisor_cancel(self, request_info, **kwargs):
        """
        Cancel a running Feed Lifecycle Advisor agent job.

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
                        "Cancel a running Feed Lifecycle Advisor agent job. "
                        "Best-effort — tool calls in flight may still "
                        "complete, but the job record is marked "
                        "``cancelled`` immediately so the UI stops polling "
                        "for a meaningful result."
                    ),
                    "resource_desc": (
                        "Cancel a running Feed Lifecycle Advisor agent job"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_feed_lifecycle/lifecycle_advisor_cancel" '
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

        logger.info(f'function=delete_lifecycle_advisor_cancel, job_id="{job_id}"')

        return {"payload": {"status": "cancelled"}, "status": 200}
