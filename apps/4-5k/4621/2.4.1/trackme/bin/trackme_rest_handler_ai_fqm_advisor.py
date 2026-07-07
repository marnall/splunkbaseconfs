#!/usr/bin/env python
# coding=utf-8

"""
TrackMe REST Handler — FQM (Field Quality Monitoring) Advisor agent.

Endpoints:
    POST   /trackme/v2/ai_fqm_advisor/fqm_advisor         — Start agent analysis
    GET    /trackme/v2/ai_fqm_advisor/fqm_advisor_status  — Poll agent job status
    DELETE /trackme/v2/ai_fqm_advisor/fqm_advisor_cancel  — Cancel running job
"""

__name__ = "trackme_rest_handler_ai_fqm_advisor.py"
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

logger = setup_logger("trackme.rest.ai.fqm_advisor", "trackme_rest_api_ai_advisor_fqm.log")

import trackme_rest_handler

import splunklib.client as client

from trackme_libs import trackme_parse_describe_flag

from trackme_libs_ai_agents import (
    _update_agent_job,
    _release_agent_slot,
)

from trackme_libs_ai_fqm_advisor import (
    start_fqm_advisor_async,
    get_agent_job_status,
    _KV_COLLECTION_AGENT_JOBS,
)


# Caps on the wizard payload size so an enormous tracker (hundreds of
# fields with verbose value distributions) doesn't blow past the agent's
# token limit before the prompt even renders. The wizard's fieldsummary
# query already caps to 1000 events; these caps are sized so a typical
# 30-field tracker fits comfortably while a pathological one is rejected
# with a clear error rather than burning a job slot on a doomed run.
_WIZARD_PAYLOAD_MAX_FIELDS = 200
_WIZARD_PAYLOAD_MAX_BYTES = 200_000  # ~200 KB serialised JSON
_WIZARD_TRACKER_KINDS = {"cim", "non_cim", "raw"}

# Per-field caps for the optional root-context strings (Phase 5 enrichment).
# These are short labels / SPL fragments — generous limits keep legitimate
# user input flowing while rejecting pathological payloads (a 50KB
# ``splunk_search`` would silently exhaust the agent's prompt budget).
_WIZARD_CONTEXT_STRING_MAX_LEN = 4096
_WIZARD_CONTEXT_STRING_FIELDS = (
    "splunk_search",
    "breakby_fields",
    "pseudo_datamodel_name",
    "cim_datamodel",
    "cim_datamodel_dataset",
    "account_name",
)


def _validate_wizard_payload(payload):
    """Validate the shape of the wizard payload for ``mode=dictionary_generate``.

    Returns a string error message on failure, or ``None`` when the payload
    is acceptable. Validation is strict: the agent's prompt assumes a
    specific shape, and a malformed payload would either fail the Pydantic
    output schema later (after spending tokens) or, worse, produce a
    plausible-looking but wrong dictionary. We pay the cost of strictness
    upfront so failure modes surface as 400 errors at launch.

    Strict rules:
      - Must be a JSON object (dict).
      - ``tracker_name`` must be a non-empty string (used in the prompt
        narrative and the audit event).
      - ``tracker_kind`` must be one of ``cim`` / ``non_cim`` / ``raw``.
      - ``fields`` must be a list with at least one entry and at most
        ``_WIZARD_PAYLOAD_MAX_FIELDS`` entries.
      - Every field entry must be a dict with a non-empty ``field`` string.
      - Total serialised size must not exceed ``_WIZARD_PAYLOAD_MAX_BYTES``.
    """
    if payload is None:
        return "wizard_payload is required when mode=dictionary_generate."
    if not isinstance(payload, dict):
        return "wizard_payload must be a JSON object."

    tracker_name = payload.get("tracker_name")
    if not isinstance(tracker_name, str) or not tracker_name.strip():
        return "wizard_payload.tracker_name must be a non-empty string."

    tracker_kind = payload.get("tracker_kind")
    if tracker_kind not in _WIZARD_TRACKER_KINDS:
        return (
            f"wizard_payload.tracker_kind must be one of "
            f"{sorted(_WIZARD_TRACKER_KINDS)} (got {tracker_kind!r})."
        )

    fields = payload.get("fields")
    if not isinstance(fields, list) or not fields:
        return "wizard_payload.fields must be a non-empty list."
    if len(fields) > _WIZARD_PAYLOAD_MAX_FIELDS:
        return (
            f"wizard_payload.fields has {len(fields)} entries; "
            f"limit is {_WIZARD_PAYLOAD_MAX_FIELDS}."
        )
    for idx, entry in enumerate(fields):
        if not isinstance(entry, dict):
            return f"wizard_payload.fields[{idx}] must be an object."
        field_name = entry.get("field")
        if not isinstance(field_name, str) or not field_name.strip():
            return f"wizard_payload.fields[{idx}].field must be a non-empty string."

    # Optional root-context fields (Phase 5 enrichment). Each is a short
    # label / SPL fragment; reject any value that's not a string or that
    # exceeds the per-field length cap. Skipping silently when missing
    # keeps backward compatibility with any caller that doesn't yet
    # supply the context.
    for ctx_key in _WIZARD_CONTEXT_STRING_FIELDS:
        if ctx_key not in payload:
            continue
        ctx_val = payload.get(ctx_key)
        if ctx_val in (None, ""):
            # Treat empty/null as "not provided" — the wizard frontend
            # already filters these out, but accept the same shape from
            # any other client.
            continue
        if not isinstance(ctx_val, str):
            return f"wizard_payload.{ctx_key} must be a string when provided."
        if len(ctx_val) > _WIZARD_CONTEXT_STRING_MAX_LEN:
            return (
                f"wizard_payload.{ctx_key} is {len(ctx_val)} chars; "
                f"limit is {_WIZARD_CONTEXT_STRING_MAX_LEN}."
            )

    # ``event_limit`` (sample size cap from the wizard) — small positive int.
    if "event_limit" in payload and payload.get("event_limit") not in (None, ""):
        ev = payload.get("event_limit")
        if not isinstance(ev, int) or isinstance(ev, bool) or ev <= 0 or ev > 10_000_000:
            return (
                "wizard_payload.event_limit must be a positive integer "
                "(at most 10000000) when provided."
            )

    # Serialised-size cap. ``json.dumps`` errors here are extraordinarily
    # rare (the dict came from JSON parsing two lines up) but we guard
    # for symmetry with the rest of the validators.
    try:
        serialised_size = len(json.dumps(payload))
    except (TypeError, ValueError):
        return "wizard_payload contains non-JSON-serialisable values."
    if serialised_size > _WIZARD_PAYLOAD_MAX_BYTES:
        return (
            f"wizard_payload serialised to {serialised_size} bytes; "
            f"limit is {_WIZARD_PAYLOAD_MAX_BYTES}."
        )

    return None


class TrackMeHandlerAiFqmAdvisor_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiFqmAdvisor_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_ai_fqm_advisor(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ai_fqm_advisor",
            "resource_group_desc": (
                "AI FQM (Field Quality Monitoring) Advisor agent endpoints. These endpoints "
                "enable AI-powered analysis and remediation of FQM entity configurations, "
                "following a 4-layer triage (collect, dictionary, per-field verdict, threshold) "
                "to recommend or apply dictionary calibration, regex fixes, or threshold changes "
                "as appropriate."
            ),
        }
        return {"payload": response, "status": 200}

    # -----------------------------------------------------------------
    # POST /trackme/v2/ai_fqm_advisor/fqm_advisor — Start analysis
    # -----------------------------------------------------------------
    def post_fqm_advisor(self, request_info, **kwargs):
        """
        Start a FQM (Field Quality Monitoring) Advisor agent analysis for an FQM entity.

        POST body (JSON):
            tenant_id (required): Tenant identifier
            component (required): Component type — fqm
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
                        "Start a FQM (Field Quality Monitoring) Advisor "
                        "agent analysis. The agent follows a 4-layer "
                        "triage (collect → dictionary → per-field verdict "
                        "→ threshold) and recommends or applies dictionary "
                        "calibration, regex fixes, or threshold changes "
                        "as appropriate. In ``dictionary_generate`` mode "
                        "the agent runs wizard-time and proposes a "
                        "starter data dictionary from a sampled-fields "
                        "payload (no entity required; no KV access). "
                        "Component: ``fqm`` only."
                    ),
                    "resource_desc": (
                        "Start an asynchronous FQM Advisor agent run "
                        "(inspect / act / dictionary_generate)"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_fqm_advisor/fqm_advisor" '
                        'mode="post" body="{\'tenant_id\': \'mytenant\', '
                        '\'component\': \'fqm\', '
                        '\'object_id\': \'<entity_key>\', '
                        '\'mode\': \'inspect\'}"'
                    ),
                    "options": [
                        {
                            "tenant_id": (
                                "Required. The virtual tenant the entity "
                                "belongs to."
                            ),
                            "component": (
                                "Required. Must be ``fqm`` (FQM Advisor "
                                "only operates on FQM trackers)."
                            ),
                            "object": (
                                "Conditional. The entity's human-readable "
                                "name. Provide EITHER ``object`` OR "
                                "``object_id``, never both. Required for "
                                "``inspect`` / ``act`` modes; must be "
                                "OMITTED for ``dictionary_generate``."
                            ),
                            "object_id": (
                                "Conditional. The entity's KV ``_key`` "
                                "hash. Provide EITHER ``object`` OR "
                                "``object_id``, never both. Required for "
                                "``inspect`` / ``act`` modes; must be "
                                "OMITTED for ``dictionary_generate``. "
                                "Preferred when available."
                            ),
                            "wizard_payload": (
                                "Conditional. JSON object with "
                                "``tracker_name`` / ``tracker_kind`` / "
                                "``fields[]`` from the FQM wizard's "
                                "``fieldsummary``. Required for "
                                "``dictionary_generate`` mode; must be "
                                "OMITTED for ``inspect`` / ``act``."
                            ),
                            "mode": (
                                "Optional. ``inspect`` (default, "
                                "read-only with remediation "
                                "recommendations), ``act`` (analysis + "
                                "apply dictionary / regex / threshold "
                                "changes automatically), or "
                                "``dictionary_generate`` (wizard-time, "
                                "propose a starter data dictionary "
                                "from a sampled-fields payload)."
                            ),
                            "provider_name": (
                                "Optional. AI provider stanza name. "
                                "Defaults to the first configured provider."
                            ),
                            "user_context": (
                                "Optional. Free-text additional "
                                "instructions from the operator."
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
        mode = body.get("mode", "inspect")
        valid_modes = {"inspect", "act", "dictionary_generate"}

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
                        if mode == "dictionary_generate"
                        else "Missing required parameters. Required: tenant_id, component, and either object or object_id"
                    )
                },
                "status": 400,
            }

        # ``dictionary_generate`` is wizard-time — there is no entity yet,
        # so ``object`` / ``object_id`` are not applicable; the agent's
        # input comes from ``wizard_payload`` instead. Validate strictly
        # to keep the contract clean: reject any attempt to combine the
        # two input shapes.
        wizard_payload = body.get("wizard_payload")

        if mode == "dictionary_generate":
            if object_value or object_id:
                return {
                    "payload": {
                        "error": (
                            "object / object_id must not be provided in "
                            "dictionary_generate mode — there is no entity at "
                            "wizard time. Provide wizard_payload instead."
                        )
                    },
                    "status": 400,
                }
            wp_err = _validate_wizard_payload(wizard_payload)
            if wp_err:
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

            if wizard_payload is not None:
                return {
                    "payload": {
                        "error": (
                            "wizard_payload is only accepted in mode=dictionary_generate. "
                            "Drop the field for inspect / act mode."
                        )
                    },
                    "status": 400,
                }

        valid_components = {"fqm"}
        if component not in valid_components:
            return {
                "payload": {
                    "error": f"Invalid component '{component}'. FQM Advisor supports: {sorted(valid_components)}."
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

        # Resolve object/object_id — only for inspect / act modes; the
        # ``dictionary_generate`` path operates wizard-time and has no
        # entity in KV (validated above to ensure object/object_id were
        # not supplied either).
        object_name = ""
        if mode != "dictionary_generate":
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
            result = start_fqm_advisor_async(
                system_service=system_service,
                user_service=user_service,
                request_info=request_info,
                tenant_id=tenant_id,
                component=component,
                object_id=object_id or "",
                object_name=object_name,
                mode=mode,
                provider_name=provider_name,
                user_context=user_context,
                launched_by=launched_by,
                chat_session_id=chat_session_id,
                wizard_payload=wizard_payload,
            )

            if mode == "dictionary_generate":
                logger.info(
                    f'function=post_fqm_advisor, tenant_id="{tenant_id}", '
                    f'component="{component}", mode="{mode}", '
                    f'tracker_name="{wizard_payload.get("tracker_name", "")}", '
                    f'fields_count="{len(wizard_payload.get("fields") or [])}", '
                    f'job_id="{result.get("job_id")}"'
                )
            else:
                logger.info(
                    f'function=post_fqm_advisor, tenant_id="{tenant_id}", '
                    f'component="{component}", object_id="{object_id}", '
                    f'object_name="{object_name}", mode="{mode}", job_id="{result.get("job_id")}"'
                )

            return {"payload": result, "status": 200}

        except ValueError as e:
            return {"payload": {"error": str(e)}, "status": 400}
        except RuntimeError as e:
            return {"payload": {"error": str(e)}, "status": 429}
        except Exception as e:
            logger.error(f"FQM Advisor start failed: {e}", exc_info=True)
            return {"payload": {"error": f"Failed to start FQM Advisor: {e}"}, "status": 500}

    # -----------------------------------------------------------------
    # GET /trackme/v2/ai_fqm_advisor/fqm_advisor_status
    # -----------------------------------------------------------------
    def get_fqm_advisor_status(self, request_info, **kwargs):
        """
        Get the status of a FQM Advisor agent job.

        Query parameters:
            job_id (required): The job identifier returned by POST /fqm_advisor

        Returns:
            {
                "status": "running" | "complete" | "error" | "cancelled",
                "result": { FqmAdvisorResult } | null,
                "error": "..." | ""
            }
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Poll the status of a FQM (Field Quality "
                        "Monitoring) Advisor agent job. Returns "
                        "``running`` / ``complete`` / ``error`` / "
                        "``cancelled``, the live progress feed, and (on "
                        "completion) the structured "
                        "``FqmAdvisorResult`` payload."
                    ),
                    "resource_desc": (
                        "Poll a FQM Advisor agent job's status, "
                        "progress, and result"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_fqm_advisor/fqm_advisor_status" '
                        'mode="get" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID returned "
                                "by ``post_fqm_advisor``."
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
    # DELETE /trackme/v2/ai_fqm_advisor/fqm_advisor_cancel
    # -----------------------------------------------------------------
    def delete_fqm_advisor_cancel(self, request_info, **kwargs):
        """
        Cancel a running FQM Advisor agent job.

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
                        "Cancel a running FQM (Field Quality Monitoring) "
                        "Advisor agent job. Best-effort — tool calls in "
                        "flight may still complete, but the job record "
                        "is marked ``cancelled`` immediately so the UI "
                        "stops polling for a meaningful result."
                    ),
                    "resource_desc": (
                        "Cancel a running FQM Advisor agent job"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_fqm_advisor/fqm_advisor_cancel" '
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

        logger.info(f'function=delete_fqm_advisor_cancel, job_id="{job_id}"')

        return {"payload": {"status": "cancelled"}, "status": 200}
