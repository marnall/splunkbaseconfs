#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: handler_logging.py - Version 2.0.3
# Copyright © Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written logging from Datapunctum AG is PROHIBITED.
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
from utstream_template.factory_logger import Logger
from utstream_template.handler_abstract import HandlerAbstract
from utstream_template.service_logging import LoggingService


class ProxyHandler(PersistentServerConnectionApplication, HandlerAbstract):
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

    def handle_get(self, data: dict):
        """
        Fetching logging from the configuration
        """
        try:
            logging_service = LoggingService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            logging = logging_service.get_logging()

            return self.response(logging, http.client.OK)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post(self, data: dict):
        """
        Adding / updating / removing / ping Elastic instance
        """
        payload = json.loads(data["payload"])
        action = payload["action"]

        if action == "add":
            return self.handle_post_add(payload)
        elif action == "update":
            return self.handle_post_update(payload)
        elif action == "remove":
            return self.handle_post_remove(payload)
        elif action == "ping":
            return self.handle_post_ping(payload)
        else:
            return self.response("Invalid action", http.client.BAD_REQUEST)

    def handle_post_add(self, payload: dict):
        """
        Add a new Logger
        """
        try:
            logging_service = LoggingService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(logging_service.add_logger(payload["logger"]), http.client.CREATED)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_update(self, payload: dict):
        """
        Update a Logger
        """
        try:
            logging_service = LoggingService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(logging_service.update_logger(payload["logger"]), http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_remove(self, payload: dict):
        """
        Remove a Logger
        """
        try:
            logging_service = LoggingService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(logging_service.delete_logger(payload["id"]), http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def __handle_error(self, exception_string: str = ""):
        """
        Handle error
        """
        if "not found" in exception_string:
            return self.response("Query not found", http.client.NOT_FOUND)
        elif "Unauthorized" in exception_string:
            return self.response("Unauthorized", http.client.FORBIDDEN)
        elif "already exists" in exception_string:
            return self.response("Already exists", http.client.CONFLICT)
        elif "The current license" in exception_string:
            return self.response(exception_string, http.client.BAD_REQUEST)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
