#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_ai_config_admin.py"
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

logger = setup_logger(
    "trackme.rest.ai.config", "trackme_rest_api_ai_config.log"
)


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
    get_ai_config,
    get_ai_api_key,
    test_llm_connectivity,
    get_splunk_hosted_models,
    AIProviderError,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAiConfigAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAiConfigAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    # Test LLM connectivity
    def post_test(self, request_info, **kwargs):
        """
        | trackme url="/services/trackme/v2/ai/admin/test" mode="post" body="{'provider_name': 'my_openai'}"
        """

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                provider_name = resp_dict.get("provider_name")
        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint tests the connectivity to the configured LLM provider.",
                "resource_desc": "Send a test message to the configured AI provider and verify the connection is working.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/ai/admin/test" mode="post" body="{\'provider_name\': \'my_openai\'}"',
                "options": [
                    {
                        "provider_name": "Optional: the name of the AI provider configuration stanza to test. If omitted, the first configured provider is used.",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get service — use system_authtoken to read AI provider config and credentials
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Get config — admins must be able to probe a disabled provider
        # (the whole point of disabling is often to troubleshoot without
        # letting the provider leak into production traffic).
        config = get_ai_config(
            service, provider_name=provider_name, include_disabled=True
        )
        if not config:
            return {
                "payload": {
                    "action": "failure",
                    "response": "AI is not configured. Create an AI provider configuration in the TrackMe configuration page.",
                },
                "status": 404,
            }

        # Get API key
        api_key = get_ai_api_key(service, config["provider_name"])

        # Test connectivity
        try:
            result = test_llm_connectivity(config, api_key, service=service)
        except Exception as e:
            logger.error(
                f'function=post_test, provider_name="{provider_name}", '
                f'exception="{str(e)}"'
            )
            return {
                "payload": {
                    "action": "failure",
                    "response": f"an unexpected error occurred: {str(e)}",
                },
                "status": 500,
            }

        return {
            "payload": result,
            "status": 200 if result["success"] else 502,
        }

    # Discover available models for the splunk_hosted provider
    def get_models(self, request_info, **kwargs):
        """
        Discover available AI models from the Splunk SLIM API (splunk_hosted provider).

        GET /services/trackme/v2/ai/admin/models
        """

        describe = False

        # Check query params first (GET requests pass describe as query param)
        if kwargs.get("describe") in ("true", "True", True, "1"):
            describe = True

        if not describe:
            payload = request_info.raw_args.get("payload", "{}")
            try:
                resp_dict = (
                    payload
                    if isinstance(payload, dict)
                    else json.loads(str(payload))
                )
            except Exception:
                resp_dict = {}

            if resp_dict.get("describe") in ("true", "True", True):
                describe = True

        if describe:
            response = {
                "describe": "This endpoint discovers available AI models from the Splunk SLIM API (splunk_hosted provider).",
                "resource_desc": "List available models from the Splunk hosted SLIM API. Only works on Splunk Cloud instances with the SLIM API enabled.",
                "resource_spl_example": '| trackme url="/services/trackme/v2/ai/admin/models" mode="get"',
                "options": [],
            }
            return {"payload": response, "status": 200}

        # Get request info for configurable splunkd timeout and logging level
        reqinfo = trackme_reqinfo(
            request_info.system_authtoken, request_info.server_rest_uri
        )
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=splunkd_timeout,
        )

        # set loglevel
        logger.setLevel(reqinfo["logging_level"])

        try:
            models = get_splunk_hosted_models(service)
            return {
                "payload": {
                    "action": "success",
                    "models": models,
                },
                "status": 200,
            }
        except AIProviderError as e:
            return {
                "payload": {
                    "action": "failure",
                    "response": str(e),
                },
                "status": 502,
            }
        except Exception as e:
            logger.error(f'function=get_models, exception="{str(e)}"')
            return {
                "payload": {
                    "action": "failure",
                    "response": f"Failed to discover models: {str(e)}",
                },
                "status": 500,
            }
