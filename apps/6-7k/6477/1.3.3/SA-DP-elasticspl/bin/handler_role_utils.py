#!/usr/bin/env python3
#
# File: handler_role_utils.py - Version 1.3.3
# Copyright © Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import json
import uuid
import traceback
import http.client

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Splunk Enterprise SDK
import splunklib.client as client

# Import Datapunctum modules
from elasticspl_template.factory_logger import Logger
from elasticspl_template.handler_abstract import HandlerAbstract
from elasticspl_template.factory_dataset import DatasetFactory


class RoleUtilsHandler(PersistentServerConnectionApplication, HandlerAbstract):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, request_payload: str) -> str:
        """
        Called for a simple synchronous request
        """

        self.uuid = str(uuid.uuid4())
        self.logger = Logger(logname="handler", uuid=self.uuid)

        try:
            return self.abstract_handle(request_payload)
        except Exception:
            self.logger.exception("Failed to handle request")

            return self.response("Failed to handle request", http.client.INTERNAL_SERVER_ERROR)

    def handle_post(self, data: dict):
        """
        Various role utilities
        """
        payload = json.loads(data["payload"])
        action = payload["action"]

        if action == "get_roles_for_user":
            return self.get_roles_for_user()

        return self.response("Invalid action", http.client.BAD_REQUEST)

    def get_roles_for_user(self):
        """
        Fetching roles for a user
        """
        try:
            self.dataset_factory = DatasetFactory(uuid=self.uuid, client=client, session_key=self.session_key)
            user_dataset = self.dataset_factory.get_dataset_service("users")
            role_dataset = self.dataset_factory.get_dataset_service("roles")

            top_user_roles = user_dataset.get_by_id(self.user)["roles"]
            imported_user_roles = []

            for role in top_user_roles:
                imported_user_roles.extend(role_dataset.get_imported_roles_by_id(role))

            all_user_roles = list(set(top_user_roles + imported_user_roles))

            result = []

            for role in all_user_roles:
                result.append({"id": role, "name": role})

            return self.response(result, http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def __handle_error(self, exception_string: str = ""):
        if "not found" in exception_string:
            return self.response("Instance not found", http.client.NOT_FOUND)
        elif "Unauthorized" in exception_string:
            return self.response("Unauthorized", http.client.FORBIDDEN)
        elif "already exists" in exception_string:
            return self.response("Already exists", http.client.CONFLICT)
        elif "The current license" in exception_string:
            return self.response(exception_string, http.client.BAD_REQUEST)
        elif exception_string.startswith("Public Exception: "):
            return self.response(exception_string.replace("Public Exception: ", ""), http.client.BAD_REQUEST)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
