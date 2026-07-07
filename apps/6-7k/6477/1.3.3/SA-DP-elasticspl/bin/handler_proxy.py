#!/usr/bin/env python3
#
# File: handler_proxy.py - Version 1.3.3
# Copyright © Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written proxy from Datapunctum AG is PROHIBITED.
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
from elasticspl_template.service_proxy import ProxyService


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
        Fetching proxy from the configuration
        """
        try:
            proxy_service = ProxyService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            proxy = proxy_service.get_proxy()

            return self.response([proxy], http.client.OK)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post(self, data: dict):
        """
        Configuring proxy
        """
        payload = json.loads(data["payload"])

        try:
            proxy_service = ProxyService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            proxy = proxy_service.set_proxy(payload)

            if proxy:
                return self.response(proxy, http.client.OK)
            else:
                return self.response("Failed to configure proxy", http.client.INTERNAL_SERVER_ERROR)

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
