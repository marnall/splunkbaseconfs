#!/usr/bin/env python
# coding=utf-8

"""
TrackMe REST Handler — Concierge Advisor agent.

Endpoints:
    POST   /trackme/v2/ai_concierge_advisor/concierge_advisor
        Start a Concierge agent run.

    GET    /trackme/v2/ai_concierge_advisor/concierge_advisor_status
        Poll the agent job status.

    DELETE /trackme/v2/ai_concierge_advisor/concierge_advisor_cancel
        Cancel a running agent job.

The Concierge Advisor is the generalist member of the AI Advisor
family. Where the specialists (ML / FLX Threshold / FQM / Feed
Lifecycle / Component Health) handle curated remediation flows for
specific surfaces, the Concierge handles the long tail by grounding
itself in the live REST API catalog (PR #1313's
``GET /configuration/api_catalog``).

Architectural property carried over from PR #1293's wizard bridge:
the agent is **read-only at the SDK level**. Its MCP tool allowlist
contains only ``concierge_read``-tagged tools — no mutation surface.
Mutation flows through the consent-card click → frontend → REST.

Plan reference:
``ai-context/integrations/concierge-advisor-implementation-plan.md``.
"""

__name__ = "trackme_rest_handler_ai_concierge_advisor.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os
import sys
import json

splunkhome = os.environ["SPLUNK_HOME"]

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import import_declare_test  # noqa: F401 — Splunk import shim

from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.ai.concierge_advisor",
    "trackme_rest_api_ai_advisor_concierge.log",
)

import trackme_rest_handler

import splunklib.client as client

from trackme_libs import trackme_parse_describe_flag

from trackme_libs_ai_agents import (
    _update_agent_job,
    _release_agent_slot,
)

from trackme_libs_ai_concierge_advisor import (
    start_concierge_advisor_async,
    get_agent_job_status,
    _KV_COLLECTION_AGENT_JOBS,
)


# Surfaces accepted by the start endpoint. Mirrors the SURFACES tuple
# in trackme_libs_autodocs_catalog but redeclared here to avoid an
# extra import in this file (the catalog helpers don't otherwise
# need to be imported at REST-handler load time).
_VALID_SURFACES = {"entity", "tenant_home", "vtenants", "global"}

# Cap on the user_intent length — the agent's prompt budget is
# finite and a 100KB intent is almost certainly a mistake. 8KB is
# generous (a 200-word paragraph with breathing room).
_USER_INTENT_MAX_BYTES = 8192


def _vtenant_account_for_tenant(service, tenant_id):
    """Look up the vtenant_account record for a tenant.

    Returns the parsed dict on success, ``None`` on any failure
    (missing record, parse error, KV unavailable). The REST handler
    uses the resolved record downstream for operational caps
    (``ai_concierge_max_actions_per_proposal``,
    ``ai_concierge_rate_limit_per_minute``) and as the existence
    check for the tenant — an unknown tenant rejects the call
    rather than defaulting on. The per-tenant enablement /
    destructive gates were removed in the gate-removal refactor;
    RBAC at the REST boundary plus the consent card's per-action
    typed-confirmation flow are the authoritative safety layers.
    """
    try:
        records = service.kvstore["kv_trackme_virtual_tenants"].data.query(
            query=json.dumps({"_key": tenant_id})
        )
    except Exception as exc:
        logger.warning(
            f"_vtenant_account_for_tenant: KV lookup failed for "
            f"tenant_id={tenant_id!r}: {exc}"
        )
        return None
    if not records:
        return None
    record = records[0]
    raw = record.get("vtenant_account") or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


class TrackMeHandlerAiConciergeAdvisor_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiConciergeAdvisor_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_ai_concierge_advisor(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ai_concierge_advisor",
            "resource_group_desc": (
                "AI Concierge Advisor agent endpoints. The Concierge is the "
                "generalist member of the AI Advisor family — it handles user "
                "requests that don't match a specialist advisor by grounding "
                "itself in the live TrackMe REST API catalog and proposing "
                "structured action contracts for explicit user consent. The "
                "agent is read-only at the SDK level; mutation flows through "
                "the consent-card click."
            ),
        }
        return {"payload": response, "status": 200}

    # -----------------------------------------------------------------
    # POST /trackme/v2/ai_concierge_advisor/concierge_advisor — Start
    # -----------------------------------------------------------------

    def post_concierge_advisor(self, request_info, **kwargs):
        """
        Start a Concierge Advisor agent run.

        POST body (JSON):
            tenant_id (required): Tenant identifier.
            surface (required): Chat surface — one of "entity",
                "tenant_home", "vtenants", "global". Filters the
                agent's discovery scope.
            user_intent (required): Free-text user intent from the
                chat. The agent translates this into action proposals.
            provider_name (optional): AI provider stanza name.
                Defaults to the first configured provider.
            user_context (optional): Free-text additional instructions
                from the operator (e.g. "do not propose destructive
                actions even if I asked").
            launched_by (optional): "ui" (default) or "ai_assistant".
            chat_session_id (optional): When launched_by="ai_assistant",
                the chat session that proposed this launch. Threaded
                through the audit trail.

        Returns:
            {"job_id": "uuid", "status": "running"}
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Start a Concierge Advisor agent run. The Concierge is "
                        "the generalist member of the AI Advisor family — it "
                        "handles user requests that don't match a specialist "
                        "advisor by grounding itself in the live REST API "
                        "catalog and proposing structured action contracts "
                        "for explicit user consent. The agent has zero write "
                        "tools at the SDK level; mutation flows through the "
                        "consent-card click. Authorisation is splunkd RBAC "
                        "at the REST boundary (the user's effective roles "
                        "must permit the proposed endpoint's required "
                        "capability); destructive actions additionally "
                        "require per-action typed confirmation in the "
                        "consent card. Tenant-level operational cap: "
                        "``ai_concierge_max_actions_per_proposal`` (default "
                        "10) — the Concierge will not propose more actions "
                        "than this in a single contract."
                    ),
                    "resource_desc": (
                        "Start an asynchronous Concierge Advisor agent run "
                        "for a user intent expressed in free text"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_concierge_advisor/concierge_advisor" '
                        'mode="post" body="{\'tenant_id\': \'mytenant\', '
                        '\'surface\': \'entity\', '
                        '\'user_intent\': \'increase priority to critical\'}"'
                    ),
                    "options": [
                        {
                            "tenant_id": (
                                "Required. The virtual tenant the request "
                                "operates against. Must be a non-empty "
                                "string matching an existing tenant."
                            ),
                            "surface": (
                                "Required. Chat surface the agent grounds "
                                "itself in — one of "
                                f"{sorted(_VALID_SURFACES)}. Determines "
                                "which subset of the REST catalog the "
                                "agent considers."
                            ),
                            "user_intent": (
                                "Required. Free-text user intent from the "
                                "chat. Non-empty, max 8KB. The agent "
                                "translates this into action proposals."
                            ),
                            "provider_name": (
                                "Optional. AI provider stanza name. "
                                "Defaults to the first configured provider."
                            ),
                            "user_context": (
                                "Optional. Free-text additional "
                                "instructions from the operator (e.g. "
                                "\"do not propose destructive actions even "
                                "if I asked\")."
                            ),
                            "launched_by": (
                                "Optional. ``ui`` (default) or "
                                "``ai_assistant``. Tagged on the audit "
                                "event so dashboards can attribute runs."
                            ),
                            "chat_session_id": (
                                "Optional. When ``launched_by="
                                "ai_assistant``, the chat session that "
                                "proposed this launch. Threaded through "
                                "the audit trail."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        # Parse + validate body.
        try:
            body = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "payload": {"error": f"Invalid JSON in request body: {exc}"},
                "status": 400,
            }

        tenant_id = body.get("tenant_id")
        surface = body.get("surface")
        user_intent = body.get("user_intent")
        provider_name = body.get("provider_name")
        user_context = body.get("user_context")
        launched_by = body.get("launched_by", "ui")
        chat_session_id = body.get("chat_session_id", "")

        if not tenant_id or not isinstance(tenant_id, str):
            return {
                "payload": {
                    "error": "Missing required parameter: tenant_id (non-empty string)",
                },
                "status": 400,
            }
        if not surface or surface not in _VALID_SURFACES:
            return {
                "payload": {
                    "error": (
                        f"Missing or invalid surface={surface!r}. "
                        f"Valid: {sorted(_VALID_SURFACES)}."
                    ),
                },
                "status": 400,
            }
        if not user_intent or not isinstance(user_intent, str) or not user_intent.strip():
            return {
                "payload": {
                    "error": "Missing required parameter: user_intent (non-empty string)",
                },
                "status": 400,
            }
        if len(user_intent.encode("utf-8")) > _USER_INTENT_MAX_BYTES:
            return {
                "payload": {
                    "error": (
                        f"user_intent exceeds {_USER_INTENT_MAX_BYTES} bytes. "
                        "Trim the request — the agent's prompt budget is finite."
                    ),
                },
                "status": 400,
            }
        if launched_by not in ("ui", "ai_assistant"):
            return {
                "payload": {
                    "error": (
                        f"Invalid launched_by={launched_by!r}. "
                        "Valid: 'ui', 'ai_assistant'."
                    ),
                },
                "status": 400,
            }

        # Build splunklib services.
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
        except Exception as exc:
            logger.error(
                f"post_concierge_advisor: failed to build splunklib services: {exc}"
            )
            return {
                "payload": {
                    "error": f"failed to build splunklib services: {exc}",
                },
                "status": 500,
            }

        # Check if AI features are enabled (server-side enforcement).
        # Mirrors the gate every other AI advisor handler and the AI chat
        # handler implement. The Concierge was the only POST endpoint
        # missing this check — the system-wide ``enable_ai_assistant=0``
        # admin kill switch is meant to silence every AI surface.
        try:
            trackme_settings = system_service.confs["trackme_settings"]
            for stanza in trackme_settings:
                if stanza.name == "trackme_general":
                    if stanza.content.get("enable_ai_assistant", "1") == "0":
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "AI features are disabled by the administrator.",
                                "error_type": "ai_disabled",
                            },
                            "status": 403,
                        }
                    break
        except Exception:
            pass  # If we can't read the setting, default to enabled

        # Tenant lookup — used downstream for operational caps
        # (``ai_concierge_max_actions_per_proposal``,
        # ``ai_concierge_rate_limit_per_minute``). The per-tenant
        # enablement gate (``ai_concierge_enabled``) and destructive
        # gate (``ai_concierge_allow_destructive``) were removed in
        # the gate-removal refactor: TrackMe RBAC is the authoritative
        # gate at the REST boundary, and the consent card's per-action
        # typed-confirmation flow is the UX-belt-and-suspenders for
        # destructive actions. Two redundant per-tenant gates added
        # nothing beyond what RBAC + the typed-confirmation already
        # enforce. They also broke the Virtual Tenants chat surface
        # (no single ``tenant_id`` in scope → gate failed closed).
        vtenant_account = _vtenant_account_for_tenant(system_service, tenant_id)
        if vtenant_account is None:
            return {
                "payload": {
                    "error": (
                        f"could not load vtenant_account for tenant {tenant_id!r}. "
                        "The Concierge Advisor requires a valid tenant configuration."
                    ),
                },
                "status": 404,
            }

        # Start the agent run.
        try:
            response = start_concierge_advisor_async(
                system_service=system_service,
                user_service=user_service,
                request_info=request_info,
                tenant_id=tenant_id,
                surface=surface,
                user_intent=user_intent,
                provider_name=provider_name,
                user_context=user_context,
                launched_by=launched_by,
                chat_session_id=chat_session_id,
                vtenant_account=vtenant_account,
            )
        except RuntimeError as exc:
            # Capacity-limit failures from the agent slot tracker.
            return {
                "payload": {"error": str(exc)},
                "status": 429,
            }
        except Exception as exc:
            logger.exception(
                f"post_concierge_advisor: failed to start agent: {exc}"
            )
            return {
                "payload": {"error": f"failed to start agent: {exc}"},
                "status": 500,
            }

        logger.info(
            f"Concierge Advisor agent started: "
            f"tenant_id={tenant_id!r}, surface={surface!r}, "
            f"launched_by={launched_by!r}, chat_session_id={chat_session_id!r}, "
            f"job_id={response.get('job_id')!r}"
        )

        return {"payload": response, "status": 200}

    # -----------------------------------------------------------------
    # GET /trackme/v2/ai_concierge_advisor/concierge_advisor_status
    # -----------------------------------------------------------------

    def get_concierge_advisor_status(self, request_info, **kwargs):
        """
        Poll the status of a Concierge Advisor agent run.

        GET query parameters:
            job_id (required): The agent job UUID returned by
                ``post_concierge_advisor``.

        Returns one of:
            {"status": "running", "job_id": ..., "progress": [...]}
                — agent still active. ``progress`` is a list of
                tool-call events the agent has emitted so far,
                suitable for rendering a live progress feed.

            {"status": "complete", "job_id": ..., "result": {...},
             "progress": [...]}
                — agent finished. ``result`` is the structured
                ``ConciergeProposalResult`` (parsed from JSON).

            {"status": "error", "job_id": ..., "error": "...",
             "progress": [...]}
                — agent failed. ``error`` is a short string.

            {"status": "cancelled", "job_id": ..., "progress": [...]}
                — caller invoked cancel.
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Poll the status of a Concierge Advisor agent run. "
                        "Returns the current status (``running`` / "
                        "``complete`` / ``error`` / ``cancelled``), the live "
                        "progress feed (tool-call events), and on completion "
                        "the structured ``ConciergeProposalResult`` (the "
                        "consent-card payload). Frontend polls this every "
                        "few seconds while the agent runs to drive the chat "
                        "panel's progress feed."
                    ),
                    "resource_desc": (
                        "Poll a Concierge Advisor agent job's status, "
                        "progress, and (when complete) result"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_concierge_advisor/concierge_advisor_status" '
                        'mode="get" body="{\'job_id\': \'abc123\'}"'
                    ),
                    "options": [
                        {
                            "job_id": (
                                "Required. The agent job UUID returned by "
                                "``post_concierge_advisor``."
                            ),
                        }
                    ],
                },
                "status": 200,
            }

        # Parse query.
        try:
            body = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "payload": {"error": f"Invalid JSON in request body: {exc}"},
                "status": 400,
            }

        job_id = body.get("job_id")
        if not job_id or not isinstance(job_id, str):
            return {
                "payload": {
                    "error": "Missing required parameter: job_id (non-empty string)",
                },
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
        except Exception as exc:
            return {
                "payload": {
                    "error": f"failed to build splunklib service: {exc}",
                },
                "status": 500,
            }

        try:
            status = get_agent_job_status(system_service, job_id)
        except Exception as exc:
            logger.exception(
                f"get_concierge_advisor_status: failed to fetch status for "
                f"job_id={job_id!r}: {exc}"
            )
            return {
                "payload": {
                    "error": f"failed to fetch agent job status: {exc}",
                },
                "status": 500,
            }

        if status is None:
            return {
                "payload": {
                    "error": f"job_id={job_id!r} not found",
                },
                "status": 404,
            }

        return {"payload": status, "status": 200}

    # -----------------------------------------------------------------
    # DELETE /trackme/v2/ai_concierge_advisor/concierge_advisor_cancel
    # -----------------------------------------------------------------

    def delete_concierge_advisor_cancel(self, request_info, **kwargs):
        """
        Cancel a running Concierge Advisor agent run.

        DELETE query parameters:
            job_id (required): The agent job UUID to cancel.

        Cancellation is best-effort: the agent's running thread checks
        the job's ``cancelled`` flag at every model-call boundary and
        bails out cleanly. Long-running tool calls (a slow REST loop-
        back, an LLM call mid-flight) may run to completion before
        the cancellation lands; the job record is marked
        ``cancelled`` immediately so the UI stops polling for a
        meaningful result.

        Returns ``{"status": "cancelled", "job_id": ...}`` on success,
        ``{"error": "..."}`` on failure (unknown job, terminal job
        state).
        """
        describe = trackme_parse_describe_flag(request_info)
        if describe:
            return {
                "payload": {
                    "describe": (
                        "Cancel a running Concierge Advisor agent run. "
                        "Best-effort — long-running tool calls (a slow REST "
                        "loopback, an LLM call mid-flight) may run to "
                        "completion before the cancellation lands, but the "
                        "job record is marked ``cancelled`` immediately so "
                        "the UI stops polling for a meaningful result."
                    ),
                    "resource_desc": (
                        "Cancel a running Concierge Advisor agent job"
                    ),
                    "resource_spl_example": (
                        '| trackme url="/services/trackme/v2/ai_concierge_advisor/concierge_advisor_cancel" '
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

        try:
            body = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "payload": {"error": f"Invalid JSON in request body: {exc}"},
                "status": 400,
            }

        job_id = body.get("job_id")
        if not job_id or not isinstance(job_id, str):
            return {
                "payload": {
                    "error": "Missing required parameter: job_id (non-empty string)",
                },
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
        except Exception as exc:
            return {
                "payload": {
                    "error": f"failed to build splunklib service: {exc}",
                },
                "status": 500,
            }

        try:
            current = get_agent_job_status(system_service, job_id)
        except Exception as exc:
            return {
                "payload": {
                    "error": f"failed to fetch agent job status: {exc}",
                },
                "status": 500,
            }

        if current is None:
            return {
                "payload": {"error": f"job_id={job_id!r} not found"},
                "status": 404,
            }

        # Refuse to cancel terminal jobs — surfacing a no-op as a
        # success would mislead the UI into thinking it had a fresh
        # cancellation to act on.
        terminal_status = current.get("status") in ("complete", "error", "cancelled")
        if terminal_status:
            return {
                "payload": {
                    "error": (
                        f"job_id={job_id!r} is already in terminal state "
                        f"{current.get('status')!r} — nothing to cancel"
                    ),
                    "current_status": current.get("status"),
                },
                "status": 409,
            }

        try:
            _update_agent_job(system_service, job_id, status="cancelled")
        except Exception as exc:
            logger.exception(
                f"delete_concierge_advisor_cancel: failed to mark job "
                f"{job_id!r} as cancelled: {exc}"
            )
            return {
                "payload": {
                    "error": f"failed to cancel agent job: {exc}",
                },
                "status": 500,
            }

        # Best-effort slot release. The agent thread also calls
        # ``_release_agent_slot`` in its ``finally`` block when it
        # actually exits, so this is belt-and-suspenders for cases
        # where a long-running tool call might keep the slot held
        # past the user's cancellation deadline. The helper is
        # idempotent via ``_released_slots[job_id]`` — duplicate
        # release here AND in the worker is fine.
        try:
            _release_agent_slot(job_id)
        except Exception:
            pass

        logger.info(
            f"Concierge Advisor agent cancelled: job_id={job_id!r}"
        )

        return {
            "payload": {"status": "cancelled", "job_id": job_id},
            "status": 200,
        }
