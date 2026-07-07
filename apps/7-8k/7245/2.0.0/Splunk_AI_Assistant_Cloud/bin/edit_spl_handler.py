import json
import os
import sys
import time
import uuid

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from base_rest import BaseRestUtils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.remote.factory import SaiaApiFactory
from spl_gen.utils import deterministic_hash, get_app_version, log_kwargs
from spl_gen.utils.audit_logging import (
    generate_ai_service_usage_log,
    generate_chat_audit_log,
)


class OneshotEditSPLHandler(PersistentServerConnectionApplication, BaseRestUtils):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        super(BaseRestUtils, self).__init__()

    def handle(self, in_bytes):
        return self.handle_wrapper(
            in_bytes, self.handle_func, require_source_app_id=False
        )

    def handleStream(self, handle, in_bytes):
        """
        For future use
        """
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

    def build_edit_user_prompt(self, spl, prompt):
        return (
            "Edit the following SPL query according to the user's instructions.\n\n"
            f"Edit Instructions:\n{prompt}\n\n"
            f"Original SPL:\n```spl\n{spl}\n```"
        )

    def handle_oneshot_editspl_generation(
        self,
        saia_api,
        params,
        job_id,
        locale,
        should_log_telemetry,
        source_app_id,
        system_scoped_service,
        user,
        trace_context_headers=None,
    ):
        """
        Handle the oneshot-editspl generation request.
        """
        if "spl" not in params or "prompt" not in params:
            return self.create_response({"error": "Incorrect arguments provided"}, 400)

        user_prompt = self.build_edit_user_prompt(params["spl"], params["prompt"])
        parsed_payload = self.parse_mcp_request_payload(params, user_prompt=user_prompt)

        if isinstance(parsed_payload, dict):
            return parsed_payload
        chat_history, additional_context = parsed_payload

        if self.V2_FLAG:
            generate_chat_audit_log(
                system_scoped_service,
                request_id=job_id,
                chat_id="oneshot",
                user=user,
                role="user",
                content=user_prompt,
            )
            request_kwargs = dict(
                job_id=job_id,
                user_prompt=user_prompt,
                chat_history=chat_history,
                locale=locale,
                log_to_telemetry=should_log_telemetry,
                source_app_id=source_app_id,
                additional_context=additional_context,
            )
            if trace_context_headers:
                request_kwargs["request_headers"] = trace_context_headers
            result = saia_api.spl_edit(**request_kwargs)
            result_body = result.json()
            edited_spl = result_body["spl"]
        else:
            request_kwargs = dict(
                job_id=job_id,
                user_prompt=user_prompt,
                chat_history=json.dumps(chat_history),
                classification=0,
                locale=locale,
                log_to_telemetry=should_log_telemetry,
                was_chat_empty=False,
                source_app_id=source_app_id,
                ast="",
                rag_data_only=False,
                rewrite_content=False,
                use_state_streamer=False,
                additional_context=additional_context,
            )
            if trace_context_headers:
                request_kwargs["request_headers"] = trace_context_headers
            result = saia_api.search(**request_kwargs)
            edited_spl = result.text

        end_time = time.time()

        generate_chat_audit_log(
            system_scoped_service,
            request_id=job_id,
            chat_id="oneshot",
            user=user,
            role="assistant",
            content=edited_spl,
        )

        generate_ai_service_usage_log(
            system_scoped_service,
            request_id=job_id,
            time=end_time,
            user=user,
            prompt_types=["Edit SPL"],
            status=200,
            source_app_id=source_app_id,
        )

        return self.create_response(json.dumps({"response": edited_spl}), 200)

    def handle_func(self, request):
        service = self.service_from_request(request)
        system_scoped_service = self.service_from_request(
            request, use_system_token=True
        )
        app_version = get_app_version(system_scoped_service)
        session = request["session"]
        user = session["user"]
        hashed_user = deterministic_hash(user)
        query_params = self.get_query_params(request)
        job_id = str(uuid.uuid4())
        source_app_id = self.get_header_value(request, self.SOURCE_APP_ID_KEY)
        trace_context_headers = self.get_trace_context_headers(request)
        request_payload = json.loads(request.get("payload", "{}"))
        params = request_payload if request_payload else query_params

        ns = request["ns"]
        if "lang" in request:
            locale = request["lang"]
        else:
            locale = "en-US"

        should_log_telemetry, _ = self._fetch_telemetry_details(
            service, request, "oneshot-edit-spl"
        )

        self.logger.info(
            log_kwargs(
                UUID=job_id,
                user=hashed_user,
                source_app=ns["app"],
                chat_id="oneshot-edit-spl",
                message="Generating one-shot-edit-spl SPL",
                saia_app_version=app_version,
            )
        )

        saia_api = SaiaApiFactory.from_rest_handler(
            self,
            service,
            system_scoped_service,
            user,
            "oneshot-edit-spl",
            hashed_user,
        )
        return self.handle_oneshot_editspl_generation(
            saia_api,
            params,
            job_id,
            locale,
            should_log_telemetry,
            source_app_id,
            system_scoped_service,
            user,
            trace_context_headers,
        )
