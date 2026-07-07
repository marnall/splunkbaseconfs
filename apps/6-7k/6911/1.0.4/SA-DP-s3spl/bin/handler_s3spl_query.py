#!/usr/bin/env python3.7
#
# File: handler_s3spl_query.py - Version 1.0.4
# Copyright (c) Datapunctum AG 2024-11-22
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
from s3spl_template.factory_logger import Logger
from s3spl_template.handler_abstract import HandlerAbstract

from s3spl.service_query import QueryService


class QueryHandler(PersistentServerConnectionApplication, HandlerAbstract):
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
            self.logger.error(traceback.format_exc())

            return self.response("Failed to handle request", http.client.INTERNAL_SERVER_ERROR)

    def handle_get(self, data: dict):
        """
        Fetching queries from the configuration
        """
        try:
            s3spl_query_service: QueryService = QueryService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            s3spl_queries: list[dict] = s3spl_query_service.get_queries()

            return self.response(s3spl_queries, http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post(self, data: dict):
        """
        Adding / updating / removing queries
        """
        payload = json.loads(data["payload"])
        action = payload["action"]

        if action == "add":
            return self.handle_post_add(payload)
        elif action == "update":
            return self.handle_post_update(payload)
        elif action == "remove":
            return self.handle_post_remove(payload)
        else:
            return self.response("Unknown action", http.client.BAD_REQUEST)

    def handle_post_add(self, payload: dict):
        """
        Adding queries
        """
        try:
            s3spl_query_service: QueryService = QueryService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(s3spl_query_service.add_query(payload["query"]), http.client.CREATED)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_update(self, payload: dict):
        """
        Updating queries
        """
        try:
            s3spl_query_service: QueryService = QueryService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(s3spl_query_service.update_query(payload["query"]), http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_remove(self, payload: dict):
        """
        Removing queries
        """
        try:
            s3spl_query_service: QueryService = QueryService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(s3spl_query_service.remove_query(payload["query"]), http.client.OK)
        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def __handle_error(self, exception_string: str = ""):
        if exception_string.startswith("Invalid Configuration"):
            return self.response(exception_string.replace("Invalid Configuration: ", ""), http.client.BAD_REQUEST)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
