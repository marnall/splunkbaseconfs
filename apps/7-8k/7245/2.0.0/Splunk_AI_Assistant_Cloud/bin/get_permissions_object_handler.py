"""
GetPermissionsObjectHandler

Persistent REST handler that serves `GET /get_permissions_object` for the SAIA Splunk app.

- Response schema: JSON object with:
  - `third_party_llm_enabled`: whether external LLM integration is enabled.
  - `permissions_object`: allowed indexes, sourcetypes, roles, and metadata for the user.
"""

import os
import sys
import uuid

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from base_rest import BaseRestUtils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.constants import FEATURE_FLAG_EXTERNAL_LLM_AVAILABLE
from spl_gen.metadata.collection import MetadataCollection
from spl_gen.metadata.manager import MetadataManager
from spl_gen.permission_utils import build_permissions_obj
from spl_gen.remote.v1alpha1 import SaiaApi
from spl_gen.utils import (
    deterministic_hash,
    get_app_version,
    get_enabled_feature_flags,
    log_kwargs,
)


class GetPermissionsObjectHandler(PersistentServerConnectionApplication, BaseRestUtils):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        super(BaseRestUtils, self).__init__()

    def handle(self, in_bytes):
        return self.handle_wrapper(in_bytes, self.handle_func)

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

    def handle_func(self, request):
        """
        Handle GET /get_permissions_object.

        - Builds Splunk service clients (user and system-scoped) and logging context.
        - Refreshes feature metadata (falls back to cached KV on failure).
        - Returns third-party LLM enablement and the current user's permissions object.
        """
        if request["method"] != "GET":
            return self.create_response({"error": "Method not allowed."}, 425)

        service = self.service_from_request(request)
        system_scoped_service = self.service_from_request(
            request, use_system_token=True
        )
        session = request["session"]
        request_id = str(uuid.uuid4())
        hashed_user = deterministic_hash(session["user"])
        source_app_id = request["header_map"][self.SOURCE_APP_ID_KEY]
        app_version = get_app_version(system_scoped_service)
        locale = request.get("lang") or "en-US"

        logging_context = dict(
            request_id=request_id,
            user=hashed_user,
            source_app=source_app_id,
            saia_app_version=app_version,
        )

        self.logger.info(
            log_kwargs(
                message="Handling permissions object fetch request.",
                **logging_context,
            )
        )

        metadata_collection = MetadataCollection(service)
        # Permissions metadata still flows through the v1 metadata APIs, so keep v1 hardcoded.
        api_client = SaiaApi(
            service, system_scoped_service, session["user"], None, hashed_user
        )
        metadata_manager = MetadataManager(
            system_scoped_service,
            metadata_collection,
            api_client,
            session["user"],
            locale,
        )

        try:
            metadata_entry = metadata_manager.get(request_id, fetch_latest=True)
        except Exception as e:
            self.logger.error(
                log_kwargs(
                    message=f"Unable to refresh feature flags, falling back to cache: {repr(e)}",
                    **logging_context,
                )
            )
            metadata_entry = metadata_collection.get()

        feature_settings = (
            metadata_entry.get(MetadataCollection.KEY_FEATURE_SETTINGS, {}) or {}
        )
        enabled_feature_flags = get_enabled_feature_flags(feature_settings)
        permissions_object = build_permissions_obj(
            service, session["user"], self.logger
        )
        third_party_llm_enabled = (
            FEATURE_FLAG_EXTERNAL_LLM_AVAILABLE in enabled_feature_flags
        )

        response_payload = {
            "third_party_llm_enabled": third_party_llm_enabled,
            "permissions_object": permissions_object,
        }

        return self.create_response(response_payload, 200)
