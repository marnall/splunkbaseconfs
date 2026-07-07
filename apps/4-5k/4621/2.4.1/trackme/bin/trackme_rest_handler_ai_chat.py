#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_ai_chat.py"
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

logger = setup_logger("trackme.rest.ai.chat", "trackme_rest_api_ai_chat.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    get_splunkd_timeout,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_reqinfo,
)
from trackme_libs_ai import (
    start_chat_request_async,
    get_job_status,
    cancel_chat_job,
    list_ai_providers,
    AINotConfiguredError,
    AIProviderError,
    AIBusyError,
    ENTITY_TYPE_MAP,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAiChat_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiChat_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Resource group description
    def get_resource_group_desc_ai(self, request_info, **kwargs):
        response = {
            "resource_group_name": "ai",
            "resource_group_desc": "AI assistant endpoints for TrackMe. These endpoints enable interactive AI-powered investigation of entity health, anomaly detection, and configuration assistance.",
        }

        return {"payload": response, "status": 200}

    # AI Chat endpoint
    def post_chat(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/ai/chat" mode="post" body="{'tenant_id': 'mytenant', 'object_category': 'splk-dsm', 'object': 'myindex:mysourcetype', 'messages': [{'role': 'user', 'content': 'Why is this entity in red state?'}]}"
        """

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        # Valid context types — single definition used for both
        # request validation and describe output
        all_context_types = (
            "entity", "vtenants", "tenant_home",
            "fqm_dictionary_wizard",
            "rest_api_reference", "backup_restore",
            "maintenance_mode", "maintenance_kdb",
            "bank_holidays", "license",
        )

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:

                # Parse context_type (defaults to "entity" for backward compatibility)
                context_type = resp_dict.get("context_type", "entity")
                if context_type not in all_context_types:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f'invalid context_type="{context_type}", valid values are: {", ".join(all_context_types)}',
                        },
                        "status": 400,
                    }

                # Entity-level fields are required only for entity context
                tenant_id = None
                object_category = None
                object_value = None

                if context_type == "entity":
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

                    try:
                        object_value = resp_dict["object"]
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "the object is required",
                            },
                            "status": 500,
                        }

                elif context_type == "tenant_home":
                    # Tenant Home requires tenant_id but not object_category/object
                    try:
                        tenant_id = resp_dict["tenant_id"]
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "the tenant_id is required for tenant_home context",
                            },
                            "status": 500,
                        }

                elif context_type == "fqm_dictionary_wizard":
                    # Wizard-time chat surface — same scoping as tenant_home
                    # (single tenant, no entity yet) so we require tenant_id
                    # and reject object_category/object if supplied (they'd be
                    # meaningless: no entity exists during wizard creation).
                    try:
                        tenant_id = resp_dict["tenant_id"]
                    except Exception as e:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": (
                                    "the tenant_id is required for "
                                    "fqm_dictionary_wizard context"
                                ),
                            },
                            "status": 500,
                        }

                try:
                    messages = resp_dict["messages"]
                except Exception as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "the messages array is required",
                        },
                        "status": 500,
                    }

                # Validate messages format
                if not isinstance(messages, list) or not messages:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": "messages must be a non-empty array of {role, content} objects",
                        },
                        "status": 500,
                    }

                for msg in messages:
                    if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "each message must have 'role' and 'content' fields",
                            },
                            "status": 500,
                        }
                    # Only user/assistant roles allowed — system prompt is server-controlled
                    if msg.get("role") not in ("user", "assistant"):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid message role: '{msg.get('role')}'. Only 'user' and 'assistant' roles are allowed.",
                            },
                            "status": 400,
                        }

                # Parse optional provider_name (selects which AI provider config to use)
                provider_name = resp_dict.get("provider_name", None)
                if provider_name is not None:
                    if not isinstance(provider_name, str) or not provider_name.strip():
                        return {
                            "payload": {
                                "action": "failure",
                                "response": "provider_name must be a non-empty string",
                            },
                            "status": 400,
                        }
                    provider_name = provider_name.strip()
        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True
            context_type = "entity"

        if describe:
            response = {
                "describe": "This endpoint sends a message to the AI assistant for investigation and troubleshooting. It supports multiple context types for different TrackMe UI areas.",
                "resource_desc": "Send a chat message to the AI assistant with context from any TrackMe UI area.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/ai/chat" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_category\': \'splk-dsm\', \'object\': \'myindex:mysourcetype\', \'messages\': [{\'role\': \'user\', \'content\': \'Why is this entity in red state?\'}]}"',
                "options": [
                    {
                        "context_type": f"(Optional) The context type. Valid values: {', '.join(all_context_types)}. Default: 'entity'.",
                        "tenant_id": "The tenant identifier (required when context_type is 'entity', 'tenant_home', or 'fqm_dictionary_wizard')",
                        "object_category": f"The entity type (required when context_type is 'entity'). Valid values: {', '.join(ENTITY_TYPE_MAP.keys())}",
                        "object": "The entity identifier (required when context_type is 'entity')",
                        "messages": "Array of message objects with 'role' (user/assistant) and 'content' fields. Include full conversation history.",
                        "provider_name": "(Optional) The AI provider stanza name to use. If omitted, uses the first configured provider.",
                    }
                ],
                "examples": {
                    "entity_context": {
                        "context_type": "entity",
                        "tenant_id": "mytenant",
                        "object_category": "splk-dsm",
                        "object": "myindex:mysourcetype",
                        "messages": [{"role": "user", "content": "Why is this entity in red state?"}],
                    },
                    "vtenants_context": {
                        "context_type": "vtenants",
                        "messages": [{"role": "user", "content": "Give me a summary of all my tenants."}],
                    },
                    "tenant_home_context": {
                        "context_type": "tenant_home",
                        "tenant_id": "mytenant",
                        "messages": [{"role": "user", "content": "What is my tenant health overview?"}],
                    },
                    "fqm_dictionary_wizard_context": {
                        "context_type": "fqm_dictionary_wizard",
                        "tenant_id": "mytenant",
                        "messages": [{
                            "role": "user",
                            "content": "Can you generate the data dictionary for this tracker?",
                        }],
                    },
                    "rest_api_reference_context": {
                        "context_type": "rest_api_reference",
                        "messages": [{"role": "user", "content": "What resource groups are available?"}],
                    },
                    "backup_restore_context": {
                        "context_type": "backup_restore",
                        "messages": [{"role": "user", "content": "What is the current backup status?"}],
                    },
                    "license_context": {
                        "context_type": "license",
                        "messages": [{"role": "user", "content": "What is my license status?"}],
                    },
                },
            }

            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # System-level service for AI config, API keys, job KV store, and settings
        system_service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # User-level service for entity data reads (enforces RBAC on tenant KV stores)
        user_service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Check if AI features are enabled (server-side enforcement)
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

        # Start the async chat request (returns immediately with job_id)
        try:
            result = start_chat_request_async(
                system_service,
                user_service,
                request_info,
                tenant_id,
                object_category,
                object_value,
                messages,
                provider_name=provider_name,
                context_type=context_type,
            )
            return {"payload": result, "status": 200}

        except AINotConfiguredError as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                    "error_type": "ai_not_configured",
                },
                "status": 503,
            }

        except AIBusyError as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                    "error_type": "ai_busy",
                },
                "status": 429,
            }

        except AIProviderError as e:
            logger.error(
                f'function=post_chat, tenant_id="{tenant_id}", '
                f'object_category="{object_category}", object="{object_value}", '
                f'error_type="ai_provider_error", exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                    "error_type": "ai_provider_error",
                },
                "status": 502,
            }

        except Exception as e:
            logger.error(
                f'function=post_chat, tenant_id="{tenant_id}", '
                f'object_category="{object_category}", object="{object_value}", '
                f'exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "failure",
                    "response": f'an unexpected error occurred: {str(e)}',
                },
                "status": 500,
            }

    # AI Chat status polling endpoint
    def get_chat_status(self, request_info, **kwargs):
        """
        Poll the status of an async AI chat job.

        GET /services/trackme/v2/ai/chat_status?job_id=xxx
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint polls the status of an asynchronous AI "
                    "Assistant chat job that was previously kicked off via "
                    "POST /trackme/v2/ai/chat. It is intended to be called "
                    "repeatedly by the chat UI while the LLM is generating a "
                    "response. The response status field is one of: "
                    "'running' (still generating, partial content may be "
                    "included), 'complete' (final response in the 'response' "
                    "object with role/content and usage stats), 'error' "
                    "(LLM or pipeline failure, message in 'response'), or "
                    "'cancelled' (job released via DELETE chat_cancel). "
                    "When the job no longer exists in the KV store the "
                    "endpoint returns HTTP 404."
                ),
                "resource_desc": "Poll the status of an asynchronous AI Assistant chat job",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/ai/chat_status?job_id=550e8400-e29b-41d4-a716-446655440000"',
                "options": [
                    {
                        "job_id": "REQUIRED. The job identifier returned by POST /trackme/v2/ai/chat. Passed as a query-string parameter",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        job_id = kwargs.get("job_id")
        if not job_id:
            return {
                "payload": {
                    "action": "failure",
                    "response": "the job_id parameter is required",
                },
                "status": 400,
            }

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service — use system_authtoken for consistent KV store access
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        result = get_job_status(service, job_id)
        if result is None:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"job not found: {job_id}",
                },
                "status": 404,
            }

        # Build response based on status
        if result["status"] == "complete":
            return {
                "payload": {
                    "status": "complete",
                    "response": {
                        "role": "assistant",
                        "content": result["content"],
                    },
                    "entity_context_loaded": result["entity_context_loaded"],
                    "usage": result["usage"],
                },
                "status": 200,
            }
        elif result["status"] == "error":
            return {
                "payload": {
                    "status": "error",
                    "response": result["error"],
                    "entity_context_loaded": result["entity_context_loaded"],
                },
                "status": 200,
            }
        elif result["status"] == "cancelled":
            return {
                "payload": {
                    "status": "cancelled",
                    "response": result.get("error") or "Cancelled by client",
                    "entity_context_loaded": result["entity_context_loaded"],
                },
                "status": 200,
            }
        else:
            # Still running — return partial content
            return {
                "payload": {
                    "status": "running",
                    "partial_content": result["content"],
                    "entity_context_loaded": result["entity_context_loaded"],
                },
                "status": 200,
            }

    # AI Chat cancel endpoint — release concurrency slot when client abandons a chat
    def delete_chat_cancel(self, request_info, **kwargs):
        """
        Cancel an in-flight AI chat job and release its concurrency slot.

        When the AI Assistant panel is closed while a request is pending, the
        client stops polling but the backend job kept consuming a slot until
        completion. Call this to free the slot immediately.

        DELETE /services/trackme/v2/ai/chat_cancel?job_id=xxx
        """

        describe = trackme_parse_describe_flag(request_info)

        if describe:
            response = {
                "describe": (
                    "This endpoint cancels an in-flight asynchronous AI "
                    "Assistant chat job and releases the concurrency slot it "
                    "was holding. It is called by the chat UI when the user "
                    "closes the panel or navigates away mid-response: without "
                    "this call the backend job would continue running to "
                    "completion and keep its slot in the bounded async pool, "
                    "starving subsequent requests until it finished. The job "
                    "transitions to status='cancelled' and any subsequent "
                    "GET chat_status returns the cancellation marker. "
                    "Returns HTTP 404 if the job_id is not present in the "
                    "KV store (already finished and purged, or never existed)."
                ),
                "resource_desc": "Cancel an in-flight asynchronous AI Assistant chat job and free its concurrency slot",
                "resource_spl_example": '| trackme mode=delete url="/services/trackme/v2/ai/chat_cancel?job_id=550e8400-e29b-41d4-a716-446655440000"',
                "options": [
                    {
                        "job_id": "REQUIRED. The job identifier to cancel. Passed as a query-string parameter",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        job_id = kwargs.get("job_id")
        if not job_id:
            return {
                "payload": {
                    "action": "failure",
                    "response": "the job_id parameter is required",
                },
                "status": 400,
            }

        splunkd_port = request_info.server_rest_port
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        success, status = cancel_chat_job(service, job_id)
        if not success:
            return {
                "payload": {
                    "action": "failure",
                    "response": f"job not found: {job_id}",
                },
                "status": 404,
            }

        return {
            "payload": {"action": "success", "status": status},
            "status": 200,
        }

    # List available AI providers endpoint
    def get_providers(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/ai/providers" mode="get"
        """

        # init
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args.get("payload", "{}")))
        except Exception:
            resp_dict = {}

        if resp_dict.get("describe") in ("true", "True", True):
            describe = True

        if describe:
            response = {
                "describe": "This endpoint returns the list of configured AI providers available for the AI assistant.",
                "resource_desc": "List all configured AI providers.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/ai/providers" mode="get"',
                "options": [],
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get request info for configurable splunkd timeout and logging level
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=splunkd_timeout,
        )

        # set loglevel
        logger.setLevel(reqinfo["logging_level"])

        try:
            providers = list_ai_providers(service)
            return {
                "payload": {
                    "action": "success",
                    "providers": providers,
                },
                "status": 200,
            }
        except Exception as e:
            logger.error(f'function=get_providers, exception="{str(e)}"')
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to list AI providers: {str(e)}",
                },
                "status": 500,
            }
