import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import requests
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from base_rest import BaseRestUtils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.remote.v2alpha1 import API_ROOT_V2, API_VERSION_V2, SAIAApiV2
from spl_gen.scs_utils import ScsUtils
from spl_gen.utils import (
    deterministic_hash,
    get_app_version,
    log_kwargs,
    read_splk_content,
)
from spl_gen.utils.audit_logging import generate_chat_audit_log
from spl_gen.utils.cloud_connected.proxy_settings_utils import ProxySettingsUtils


class SaiaV2AuditIndexLogProxyHandler(
    PersistentServerConnectionApplication, BaseRestUtils
):
    AGENT_MODE_TYPE = "Agent Mode"
    CONVERSATION_FETCH_ATTEMPTS = 3
    CONVERSATION_FETCH_RETRY_DELAY_SECONDS = 0.25

    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        super(BaseRestUtils, self).__init__()

    def handle(self, in_bytes):
        return self.handle_wrapper(in_bytes, self.handle_func)

    def handleStream(self, handle, in_bytes):
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        pass

    @staticmethod
    def _normalize_ec_token(auth_token: Optional[str]) -> Optional[str]:
        if not isinstance(auth_token, str) or not auth_token:
            return None
        if auth_token.startswith("Splunk "):
            return auth_token[len("Splunk ") :]
        return auth_token

    @classmethod
    def _extract_content_text(cls, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "".join(
                cls._extract_content_text(block)
                for block in content
                if block is not None
            )

        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str):
                return text

            nested_content = content.get("content")
            if nested_content is not None:
                return cls._extract_content_text(nested_content)

            try:
                return json.dumps(content, sort_keys=True)
            except TypeError:
                return str(content)

        if content is None:
            return ""

        return str(content)

    @staticmethod
    def _sort_conversation_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            item
            for _, item in sorted(
                enumerate(items),
                key=lambda value: ((value[1] or {}).get("created_at") or "", value[0]),
            )
        ]

    def _fetch_interactive_token(self, service) -> str:
        response = service.post(
            "/services/authorization/tokens",
            type="interactive",
            output_mode="json",
        )
        content = read_splk_content(response)
        interactive_token = content.get("token")
        if not interactive_token:
            raise RuntimeError(
                {
                    "status": 403,
                    "error": "No interactive token found for SAIA V2 audit logging.",
                }
            )
        return interactive_token

    def _build_conversation_items_url(
        self, tenant_info: Dict[str, Any], chat_id: str
    ) -> str:
        tenant_hostname = tenant_info.get("tenantHostname")
        tenant_id = tenant_info.get("tenant")
        if not tenant_hostname or not tenant_id:
            raise RuntimeError(
                {
                    "status": 500,
                    "error": "Missing tenant configuration for SAIA V2 audit logging.",
                }
            )

        if not tenant_hostname.startswith("http://") and not tenant_hostname.startswith(
            "https://"
        ):
            tenant_hostname = f"https://{tenant_hostname}"

        normalized_chat_id = chat_id.strip().strip("/")
        return (
            f"{tenant_hostname}/{tenant_id}/{API_ROOT_V2}/{API_VERSION_V2}"
            f"/conversations/{normalized_chat_id}/items"
        )

    def _fetch_conversation_items(
        self,
        *,
        service,
        system_scoped_service,
        session,
        tenant_info: Dict[str, Any],
        chat_id: str,
        request_id: str,
    ) -> List[Dict[str, Any]]:
        is_cloud_stack = ScsUtils.is_cloud_stack(system_scoped_service.token)
        if is_cloud_stack:
            bearer_token = self._fetch_interactive_token(service)
            ec_token = None
            proxies = {}
        else:
            bearer_token = ScsUtils.get_scs_token_for_cmp_stack(system_scoped_service)
            ec_token = self._normalize_ec_token(
                session.get("authtoken") or getattr(service, "token", None)
            )
            proxies = ProxySettingsUtils.fetch_proxies_if_enabled(system_scoped_service)

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Request-Id": request_id,
        }
        if ec_token:
            headers["x-ec-token"] = ec_token

        url = self._build_conversation_items_url(tenant_info, chat_id)
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            error_text = getattr(response, "text", "") or response.status_code
            raise RuntimeError(
                {
                    "status": getattr(response, "status_code", 502),
                    "error": f"Failed to fetch SAIA V2 conversation items: {error_text}",
                }
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise RuntimeError(
                {
                    "status": 502,
                    "error": "Invalid SAIA V2 conversation items response.",
                }
            ) from error

        if not isinstance(payload, list):
            raise RuntimeError(
                {
                    "status": 502,
                    "error": "Unexpected SAIA V2 conversation items response format.",
                }
            )

        return payload

    def _fetch_final_assistant_turn(
        self,
        *,
        service,
        system_scoped_service,
        session,
        tenant_info: Dict[str, Any],
        chat_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        for attempt in range(self.CONVERSATION_FETCH_ATTEMPTS):
            conversation_items = self._fetch_conversation_items(
                service=service,
                system_scoped_service=system_scoped_service,
                session=session,
                tenant_info=tenant_info,
                chat_id=chat_id,
                request_id=request_id,
            )
            sorted_items = self._sort_conversation_items(conversation_items)
            if sorted_items and sorted_items[-1].get("role") == "assistant":
                return sorted_items[-1]

            if attempt < self.CONVERSATION_FETCH_ATTEMPTS - 1:
                # Allow for a short persistence lag after the streaming response completes.
                time.sleep(self.CONVERSATION_FETCH_RETRY_DELAY_SECONDS)

        raise RuntimeError(
            {
                "status": 404,
                "error": f"No completed assistant turn found for chat_id '{chat_id}'.",
            }
        )

    def handle_func(self, request):
        if request["method"] != "POST":
            return self.create_response({"error": "Method not allowed."}, 405)

        payload = self.get_payload(request)
        if set(payload.keys()) != {"chat_id"}:
            return self.create_response({"error": "Incorrect arguments provided"}, 400)

        chat_id = payload.get("chat_id")
        if not isinstance(chat_id, str) or not chat_id.strip():
            return self.create_response(
                {"error": "'chat_id' must be a non-empty string"},
                400,
            )

        service = self.service_from_request(request)
        system_scoped_service = self.service_from_request(
            request, use_system_token=True
        )
        session = request["session"]
        request_id = str(uuid.uuid4())
        hashed_user = deterministic_hash(session["user"])
        source_app_id = request["header_map"][self.SOURCE_APP_ID_KEY]
        app_version = get_app_version(system_scoped_service)

        logging_context = dict(
            request_id=request_id,
            chat_id=chat_id,
            user=hashed_user,
            source_app=source_app_id,
            saia_app_version=app_version,
        )
        self.logger.info(
            log_kwargs(
                message="Handling SAIA V2 audit index log proxy request",
                **logging_context,
            )
        )

        ScsUtils.set_logger(self.logger)
        ProxySettingsUtils.set_logger(self.logger)
        saia_api = SAIAApiV2(
            service,
            system_scoped_service,
            session["user"],
            chat_id=chat_id,
            hashed_user=hashed_user,
        )

        final_assistant_turn = self._fetch_final_assistant_turn(
            service=service,
            system_scoped_service=system_scoped_service,
            session=session,
            tenant_info=saia_api.tenant_info,
            chat_id=chat_id,
            request_id=request_id,
        )
        final_content = self._extract_content_text(final_assistant_turn.get("content"))

        generate_chat_audit_log(
            system_scoped_service,
            request_id=request_id,
            chat_id=chat_id,
            user=session["user"],
            role="assistant",
            content=final_content,
            chat_type=self.AGENT_MODE_TYPE,
        )

        self.logger.info(
            log_kwargs(
                message="Emitted SAIA V2 audit log entry",
                **logging_context,
            )
        )
        return self.create_response({"message": "success"}, 201)
