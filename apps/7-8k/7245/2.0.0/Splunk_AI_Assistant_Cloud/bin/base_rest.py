import json
import logging
import os
import sys
import uuid
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.binding import HTTPError, handler
from splunklib.client import connect
from splunklib.searchcommands import environment


class BaseRestUtils:
    API_VERSION = "1.0.0"
    CONFIG_FILE_ENDPOINT = "configs/conf-splunkaiassistant/splunk_ai_assistant"
    # TODO: Replace this static switch with the KVStore-backed V2 flag once it exists.
    V2_FLAG = True
    # Browser behaviour can be inconsistent, so lowercase both this const as well as header keys
    # inside request["header_map"]
    SOURCE_APP_ID_KEY = "Source-App-ID".lower()

    SOURCE_APP_ID_KEY_SNAKE_CASE = "Source_App_ID".lower()
    TRACE_CONTEXT_HEADER_KEYS = ("traceparent", "tracestate")

    def __init__(self):
        environment.app_root = os.path.join(os.path.dirname(__file__), "..")
        logger, _ = environment.configure_logging(self.__class__.__name__)
        if logger:
            self.logger = logger

    def _fetch_telemetry_details(self, service, request, handler_type=None):
        try:
            config_response = service.get(
                "config",
                owner="nobody",
                app=request["ns"]["app"],
                output_mode="json",
                headers=[(self.SOURCE_APP_ID_KEY, "internal")],
            )
            config = self.decode_config_response_body(config_response)

            feature_settings = config["feature_settings"]
            enabled_features = [
                key for key, val in feature_settings.items() if val["enabled"] is True
            ]

            return config.get("ai_service_data_enabled") == "1" and not (
                config.get("permanently_disable_ai_service_data") == "1"
            ), enabled_features
        except Exception:
            # telemetry shouldn't block functionality
            self.logger.info(f"Fetching telemetry details for {handler_type} handler")
            return False, []

    def validate_payload(self, payload, required_fields):
        for field in required_fields:
            if field not in payload:
                raise RuntimeError(
                    {"error": f"'{field}' missing in the payload", "status": 400}
                )

    def get_payload(self, request):
        try:
            return json.loads(request.get("payload", "{}"))
        except json.JSONDecodeError:
            raise RuntimeError(
                {"error": "request payload is not valid JSON", "status": 400}
            )

    def get_query_params(self, request):
        query = request["query"]
        query_params = {}
        for key, val in query:
            if val.lower() in ["true", "false"]:
                val = val.lower() == "true"
            query_params[key] = val

        return query_params

    def get_header_map(self, request):
        headers = request["headers"]
        header_map = defaultdict(list)
        for header_items in headers:
            key = header_items[0].lower()
            # Value should be a list only if there are multiple values for key
            header_map[key] = (
                header_items[1:] if len(header_items) > 2 else header_items[1]
            )

        return header_map

    def get_header_value(self, request, key):
        value = request["header_map"].get(key)
        if isinstance(value, list):
            return value[0] if value else None
        return value

    def get_trace_context_headers(self, request):
        trace_context_headers = {}
        for key in self.TRACE_CONTEXT_HEADER_KEYS:
            value = self.get_header_value(request, key)
            if value:
                trace_context_headers[key] = value

        return trace_context_headers

    def handle_wrapper(self, in_bytes, handle_func, require_source_app_id=True):
        """
        Called for a simple synchronous request.
        @param in_bytes: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        try:
            try:
                request = json.loads(in_bytes.decode("utf-8"))
                request["header_map"] = self.get_header_map(request)
                source_app_id = self.get_header_value(request, self.SOURCE_APP_ID_KEY)
                if source_app_id is None:
                    query_params = self.get_query_params(request)
                    if self.SOURCE_APP_ID_KEY in query_params:
                        request["header_map"][self.SOURCE_APP_ID_KEY] = query_params[
                            self.SOURCE_APP_ID_KEY
                        ]
                    elif self.SOURCE_APP_ID_KEY_SNAKE_CASE in query_params:
                        request["header_map"][self.SOURCE_APP_ID_KEY] = query_params[
                            self.SOURCE_APP_ID_KEY_SNAKE_CASE
                        ]
                    elif require_source_app_id:
                        return self.create_response(
                            {
                                "header_map": request["header_map"],
                                "headers": request["headers"],
                                "error": f"Missing required {self.SOURCE_APP_ID_KEY} header",
                            },
                            400,
                        )

                return handle_func(request)
            except json.JSONDecodeError as e:
                self.logger.error(e)
                return self.create_response(
                    payload={"error": "JSON decoding error"}, status_code=400
                )
            except RuntimeError as e:
                (content,) = e.args
                if isinstance(content, str):
                    return self.create_response(
                        payload={"error": content}, status_code=500
                    )
                elif isinstance(content, dict):
                    return self.create_response(
                        payload={"error": content["error"]},
                        status_code=content["status"],
                    )
                else:
                    return self.create_response(
                        payload={"error": "unknown error"}, status_code=500
                    )
        except Exception as e:
            logging.exception("unknown exception")
            self.logger.error(e)
            return self.create_response(payload={"error": str(e)}, status_code=500)

    def service_from_request(self, request, use_system_token=False):
        session = request["session"]
        auth_token = session["authtoken"]
        owner = session["user"]
        if use_system_token:
            if "system_authtoken" in request:
                auth_token = request["system_authtoken"]
                owner = "splunk-system-user"
            else:
                self.logger.error(
                    f"system token not available for REST handler {self.__class__.__name__}"
                )
        try:
            return connect(
                token=auth_token,
                handler=handler(timeout=1),
                host="127.0.0.1",
                app=request["ns"]["app"],
                owner=owner,
                retries=10,
                retryDelay=2,
            )
        except HTTPError as e:
            self.logger.error(e)
            raise e

    def decode_config_response_body(self, response):
        response_body = response["body"].read()
        return json.loads(response_body.decode("utf-8"))

    def create_response(self, payload, status_code):
        return {"payload": payload, "status": status_code}

    def _normalize_additional_context(self, additional_context):
        if additional_context is None:
            return None

        if isinstance(additional_context, dict):
            return additional_context

        if isinstance(additional_context, str):
            if not additional_context.strip():
                return None
            try:
                additional_context = json.loads(additional_context)
            except json.JSONDecodeError as exc:
                raise ValueError("Malformed additional_context provided") from exc

            if additional_context is None:
                return None
            if isinstance(additional_context, dict):
                return additional_context

        raise ValueError("additional_context must be a JSON object or null")

    def parse_mcp_request_payload(self, params, user_prompt=None):
        """Parses a request payload (JSON Object)
        Expects params to have:
        - prompt: string (for Write/Q&A skills) OR spl: string (for Explain/Optimize skills)
        - additional_context: JSON object or null (optional)
        - chat_history: JSON string (optional)
        Returns:
        - chat_history: list of chat turns (Chat Completions format)
        - additional_context: dict or None
        """
        if user_prompt is None:
            if "prompt" in params:
                user_prompt = params["prompt"]
            elif "spl" in params:
                user_prompt = params["spl"]
            else:
                raise KeyError("Expected either 'prompt' or 'spl' in request params")

        try:
            additional_context = self._normalize_additional_context(
                params.get("additional_context")
            )
        except ValueError as exc:
            self.logger.info(str(exc))
            return self.create_response({"error": str(exc)}, 400)

        chat_history = []
        if "chat_history" in params and params["chat_history"]:
            # Append any provided chat history to the prompt
            try:
                chat_history = json.loads(params["chat_history"])
            except json.JSONDecodeError:
                self.logger.info("Invalid chat history provided in request payload")
                # Return a 400 invalid error
                return self.create_response(
                    {"error": "Malformed chat history provided"}, 400
                )

            # If the final chat turn is not from the user, we need to add the user prompt as a new turn
            if len(chat_history) == 0 or chat_history[-1]["role"] != "user":
                chat_history.append(
                    {"content": user_prompt, "role": "user", "id": str(uuid.uuid4())}
                )
        else:
            # Make request directly to SAIA SCS API, for oneshot generation
            chat_history = [
                {"content": user_prompt, "role": "user", "id": str(uuid.uuid4())}
            ]
        return chat_history, additional_context
