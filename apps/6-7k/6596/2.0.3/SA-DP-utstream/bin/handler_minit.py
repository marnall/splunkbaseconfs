#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: handler_minit.py - Version 2.0.3
# Copyright © Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written logging from Datapunctum AG is PROHIBITED.
#

import os
import sys
import json
import uuid
import http.client

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Splunk Enterprise SDK
import splunklib.client as client

# Import Datapunctum modules
from utstream_template.factory_logger import Logger
from utstream_template.handler_abstract import HandlerAbstract
from utstream_template.service_minit import MinitService


class MinitHandler(PersistentServerConnectionApplication, HandlerAbstract):
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
        except Exception as e:
            self.logger.exception("Failed to handle request")

            return self.response("Failed to handle request", http.client.INTERNAL_SERVER_ERROR)

    def handle_get(self, data: dict):
        """
        Fetching logging from the configuration
        """
        try:
            minit_service = MinitService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            tasks = minit_service.get_all_tasks()
            self.logger.info({"action": "handle_get", "status": "success", "task_count": len(tasks)})

            return self.response(tasks, http.client.OK)

        except Exception as e:
            self.logger.exception("")
            return self.__handle_error(str(e))

    def handle_post(self, data: dict):
        """
        Run a task
        """
        payload = json.loads(data["payload"])
        action = payload["action"]

        if action == "run":
            return self.handle_post_run(payload)
        else:
            return self.response("Invalid action", http.client.BAD_REQUEST)

    def handle_post_run(self, payload: dict):
        """
        Runs a task
        """
        try:
            minit_service = MinitService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(minit_service.run_task(payload["task"]), http.client.OK)
        except Exception as e:
            self.logger.exception("")
            return self.__handle_error(str(e))

    def __handle_error(self, exception_string: str = ""):
        """
        Handle error
        """
        if "not found" in exception_string:
            return self.response("Task not found", http.client.NOT_FOUND)
        elif "Unauthorized" in exception_string:
            return self.response("Unauthorized", http.client.FORBIDDEN)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
