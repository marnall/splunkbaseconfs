import os
import sys
import traceback
import uuid
from typing import Any, Dict, Optional

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from base_rest import BaseRestUtils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.scs_utils import ScsUtils
from spl_gen.utils import (
    deterministic_hash,
    get_app_version,
    log_kwargs,
    read_splk_content,
)
from splunklib.binding import HTTPError as SplunkHTTPError


class SaiaTokenHandler(PersistentServerConnectionApplication, BaseRestUtils):
    """REST handler that returns SAIA auth tokens for frontend clients."""

    def __init__(self, _command_line, _command_arg) -> None:
        """Initialize the handler for Splunk persistent connection callbacks."""
        super(PersistentServerConnectionApplication, self).__init__()
        super(BaseRestUtils, self).__init__()

    def handle(self, in_bytes) -> Dict[str, Any]:
        """Dispatch an incoming request to :meth:`handle_func` via the wrapper."""
        return self.handle_wrapper(in_bytes, self.handle_func)

    def done(self) -> None:
        """Receive the optional completion callback after request handling."""
        pass

    def _get_secret(
        self, system_scoped_service, username, secret_key, required=True
    ) -> Optional[str]:
        """Fetch a stored secret value for a user from Splunk storage passwords.

        Raises:
            RuntimeError: If the secret is required but cannot be found.
        """
        try:
            secret = system_scoped_service.storage_passwords[
                f"{secret_key}:{username}:"
            ]
            return secret.clear_password
        except KeyError:
            if required:
                if secret_key == "api_key":
                    error = "Service not initialized, please contact support."
                else:
                    error = f"unable to fetch secret '{secret_key}'"
                raise RuntimeError(
                    {
                        "status": 403,
                        "error": error,
                    }
                )
            return None

    def _fetch_cloud_scs_token(
        self, system_scoped_service, username, logging_context
    ) -> str:
        """Return an SCS token for cloud deployments.

        Tries the native `/services/authorization/scs_tokens` endpoint first and
        falls back to the stored API key on specific authorization errors.
        """
        try:
            res = system_scoped_service.get(
                "/services/authorization/scs_tokens",
                principalId="saia",
                scope="tenant",
                output_mode="json",
            )
            content = read_splk_content(res)
            scs_token = content.get("scs_token")
        except SplunkHTTPError as e:
            if e.status in (400, 403, 404):
                self.logger.error(
                    log_kwargs(
                        message=getattr(e, "message", e),
                        **logging_context,
                    )
                )
                scs_token = self._get_secret(system_scoped_service, username, "api_key")
            else:
                self.logger.error(
                    log_kwargs(
                        message=getattr(e, "message", e),
                        **logging_context,
                    )
                )
                raise e

        self.logger.info(
            log_kwargs(
                message="Fetched SCS token.",
                **logging_context,
            )
        )
        if scs_token:
            return scs_token
        else:
            raise RuntimeError({"status": 403, "error": "No SCS token found"})

    def handle_func(self, request) -> Dict[str, Any]:
        """Handle SAIA token GET requests and return frontend auth tokens."""
        if request["method"] != "GET":
            return self.create_response({"error": "Method not allowed."}, 405)

        system_scoped_service = self.service_from_request(
            request, use_system_token=True
        )
        session = request["session"]
        logging_uuid = str(uuid.uuid4())
        hashed_user = deterministic_hash(session["user"])
        source_app_id = request["header_map"][self.SOURCE_APP_ID_KEY]
        app_version = get_app_version(system_scoped_service)

        logging_context = dict(
            request_id=logging_uuid,
            user=hashed_user,
            source_app=source_app_id,
            saia_app_version=app_version,
        )

        self.logger.info(
            log_kwargs(
                message="Handling SAIA token request",
                **logging_context,
            )
        )

        ScsUtils.set_logger(self.logger)
        is_cloud_stack = ScsUtils.is_cloud_stack(system_scoped_service.token)
        try:
            if is_cloud_stack:
                scs_token = self._fetch_cloud_scs_token(
                    system_scoped_service, session["user"], logging_context
                )
            else:
                scs_token = ScsUtils.get_scs_token_for_cmp_stack(system_scoped_service)
        except RuntimeError as e:
            content = e.args[0] if e.args else None
            if isinstance(content, dict):
                error_msg = content.get("error", "Unknown error")
                status_code = content.get("status", 500)
            else:
                error_msg = (
                    f"An exception occurred while fetching SAIA token: {repr(e)}"
                )
                status_code = 500
            self.logger.error(
                log_kwargs(
                    message=error_msg,
                    **logging_context,
                )
            )
            return self.create_response({"error": error_msg}, status_code)
        except Exception as e:
            error_msg = f"An exception occurred while fetching SAIA token: {repr(e)}"
            self.logger.error(
                log_kwargs(
                    message=error_msg,
                    error_traceback=traceback.format_exc(),
                    **logging_context,
                )
            )
            return self.create_response({"error": error_msg}, 500)

        response_payload = {
            "scs_token": scs_token,
        }
        if not is_cloud_stack:
            response_payload["ec_token"] = session["authtoken"]

        return self.create_response(response_payload, 200)
