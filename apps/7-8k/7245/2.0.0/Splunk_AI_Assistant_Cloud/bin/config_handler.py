"""
ConfigHandler

Persistent REST handler for reading and updating app configuration.

- `GET` returns merged settings and metadata, optionally enriched with tenant info.
- `POST` updates a single configuration key in either settings or metadata.
"""

import json
import os
import sys
import traceback
import uuid
from typing import Any, Dict, Literal, Optional

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from base_rest import BaseRestUtils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.metadata.collection import MetadataCollection
from spl_gen.metadata.manager import MetadataManager
from spl_gen.permission_utils import get_user_capabilities
from spl_gen.remote.v1alpha1 import SaiaApi
from spl_gen.scs_utils import ScsUtils
from spl_gen.user_settings.collection import SettingsCollection
from spl_gen.utils import deterministic_hash, get_app_version, log_kwargs
from splunklib.client import Service


class ConfigHandler(PersistentServerConnectionApplication, BaseRestUtils):
    """Serve `/config` requests for reading and mutating SAIA configuration."""

    # TODO: this endpoint is not needed at all, should use the underlying conf endpint directly from UI
    WRITE_ALLOWED_CAPABILITIES = "admin_all_objects"

    def __init__(self, _command_line: Any, _command_arg: Any) -> None:
        """Initialize Splunk persistent REST handler mixins."""
        super(PersistentServerConnectionApplication, self).__init__()
        super(BaseRestUtils, self).__init__()

    def handle(self, in_bytes: bytes) -> Dict[str, Any]:
        """Decode the request payload and dispatch to `handle_func`."""
        return self.handle_wrapper(in_bytes, self.handle_func)

    def handleStream(self, handle: Any, in_bytes: bytes) -> None:
        """
        Placeholder for stream handling.

        Streaming is currently unsupported for this endpoint.
        """
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self) -> None:
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

    def _get_manager_type_for_key(self, key: str) -> Literal["settings", "metadata"]:
        """Return which backing store should be used for a config key."""
        if key in [
            SettingsCollection.KEY_AI_SERVICE_DATA_ENABLED,
            SettingsCollection.KEY_PERMANENTLY_DISABLE_AI_SERVICE_DATA,
        ]:
            return "settings"
        else:
            return "metadata"

    def _handle_get_request(
        self,
        settings_collection: SettingsCollection,
        metadata_manager: MetadataManager,
        fetch_latest: bool,
        logging_context: Dict[str, Any],
        tenant_name: Optional[str] = None,
        tenant_hostname: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle GET by returning merged settings/metadata with optional tenant info."""
        self.logger.info(
            log_kwargs(
                message="Fetching config data.",
                **logging_context,
            )
        )

        try:
            settings = settings_collection.get()
            metadata = metadata_manager.get(
                logging_context["request_id"], fetch_latest=fetch_latest
            )
            config_content = {**settings, **metadata}
            if tenant_name:
                config_content["tenant_name"] = tenant_name
            if tenant_hostname:
                config_content["tenant_hostname"] = tenant_hostname
            return self.create_response(config_content, 200)
        except Exception as e:
            error_msg = f"An exception occurred while attempting to fetch settings and metadata: {repr(e)}"
            self.logger.error(
                log_kwargs(
                    message=error_msg,
                    **logging_context,
                )
            )
            return self.create_response({"error": error_msg}, 500)

    def _handle_post_request(
        self,
        request_payload: Dict[str, Any],
        service: Service,
        settings_collection: SettingsCollection,
        metadata_manager: MetadataManager,
        logging_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle POST by authorizing and updating exactly one configuration key."""
        key = next(iter(request_payload))
        self.logger.info(
            log_kwargs(
                message=f"Making POST request to update config key {key}.",
                **logging_context,
            )
        )

        if self.WRITE_ALLOWED_CAPABILITIES not in get_user_capabilities(service):
            error_msg = "Unauthorized attempt to update config"
            self.logger.error(
                log_kwargs(
                    message=error_msg,
                    **logging_context,
                )
            )
            return self.create_response({"error": error_msg}, 403)

        error_msg = ""
        manager_type = self._get_manager_type_for_key(key)
        config_content: Dict[str, Any] = {}
        if manager_type == "settings":
            val_to_store = (
                json.dumps(request_payload[key])
                if isinstance(request_payload[key], dict)
                else request_payload[key]
            )
            try:
                config_content = settings_collection.update({key: val_to_store})
            except Exception as e:
                self.logger.error(log_kwargs(error_traceback=traceback.format_exc()))
                error_msg = f"An exception occurred while attempting to update settings: {repr(e)}"
                res_status = 500
            else:
                res_status = 200
        else:  # manager_type == "metadata"
            try:
                config_content = metadata_manager.update(
                    logging_context["request_id"], {key: request_payload[key]}
                )
            except Exception as e:
                self.logger.error(log_kwargs(error_traceback=traceback.format_exc()))
                error_msg = f"An exception occurred while attempting to update metadata: {repr(e)}"
                res_status = 500
            else:
                res_status = 200

        if res_status == 500:
            self.logger.error(
                log_kwargs(
                    message=error_msg,
                    **logging_context,
                )
            )
            return self.create_response({"error": error_msg}, res_status)

        return self.create_response(config_content, res_status)

    def handle_func(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route the incoming Splunkd request to the GET or POST handler."""
        hashed_user = deterministic_hash(request["session"]["user"])
        service = self.service_from_request(request)
        payload = self.get_payload(request)
        system_scoped_service = self.service_from_request(
            request, use_system_token=True
        )
        logging_uuid = str(uuid.uuid4())
        source_app_id = request["header_map"][self.SOURCE_APP_ID_KEY]
        app_version = get_app_version(system_scoped_service)

        logging_context = dict(
            chat_id=getattr(payload, "chat_id", None),
            user=hashed_user,
            request_id=logging_uuid,
            source_app=source_app_id,
            saia_app_version=app_version,
        )

        self.logger.info(
            log_kwargs(
                message="Handling config request",
                **logging_context,
            )
        )

        query = request["query"]
        fetch_latest = False
        for query_pair in query:
            if query_pair[0] == "latest":
                fetch_latest = query_pair[1].lower() == "true"

        session = request["session"]
        locale = request.get("lang")
        hashed_user = deterministic_hash(request["session"]["user"])

        settings_collection = SettingsCollection(service)

        # Config sync still depends on the v1 metadata APIs, so keep v1 hardcoded here.
        saia_api = SaiaApi(
            service, system_scoped_service, session["user"], None, hashed_user
        )
        metadata_manager = MetadataManager(
            system_scoped_service,
            MetadataCollection(service),
            saia_api,
            session["user"],
            locale,
        )

        request_payload = self.get_payload(request)
        if request["method"] == "GET":
            tenant_name = None
            tenant_hostname = None
            system_token = (
                request.get("system_authtoken") or system_scoped_service.token
            )
            if ScsUtils.is_cloud_stack(system_token):
                try:
                    tenant_info = saia_api.tenant_info or {}
                    tenant_name = tenant_info.get("tenant")
                    tenant_hostname = tenant_info.get("tenantHostname")
                except Exception as e:
                    self.logger.error(
                        log_kwargs(
                            message=f"Unable to fetch tenant info: {repr(e)}",
                            **logging_context,
                        )
                    )
            return self._handle_get_request(
                settings_collection,
                metadata_manager,
                fetch_latest,
                logging_context,
                tenant_name,
                tenant_hostname,
            )
        elif request["method"] == "POST":
            return self._handle_post_request(
                request_payload,
                service,
                settings_collection,
                metadata_manager,
                logging_context,
            )

        # TODO: this needs to be more accurate
        return self.create_response({"error": "Something went wrong"}, 500)
