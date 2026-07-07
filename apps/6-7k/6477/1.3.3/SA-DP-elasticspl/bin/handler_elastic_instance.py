#!/usr/bin/env python3
#
# File: handler_elastic_instance.py - Version 1.3.3
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
from elasticspl.service_elastic_instance import ElasticInstanceService
from elasticspl.exception_elasticspl import ElasticConnectionException, ElasticApplicationException


class ElasticInstanceHandler(PersistentServerConnectionApplication, HandlerAbstract):
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
            self.logger.exception(traceback.format_exc())

            return self.response("Failed to handle request", http.client.INTERNAL_SERVER_ERROR)

    def handle_get(self, data: dict):
        """
        Fetching Elastic instances from the configuration
        """
        try:
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            elastic_instances: list[dict] = elastic_instance_service.get_instances()

            return self.response(elastic_instances, http.client.OK)
        except Exception as e:
            self.logger.exception(traceback.format_exc())
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
        Add a new Elastic instance
        """
        try:
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(elastic_instance_service.add_instance(payload["instance"]), http.client.CREATED)
        except Exception as e:
            self.logger.exception(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_update(self, payload: dict):
        """
        Update an existing Elastic instance
        """
        try:
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(elastic_instance_service.update_instance(payload["instance"]), http.client.OK)
        except Exception as e:
            self.logger.exception(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_remove(self, payload: dict):
        """
        Remove an existing Elastic instance
        """
        try:
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            return self.response(elastic_instance_service.remove_instance(payload["instance"]), http.client.OK)
        except Exception as e:
            self.logger.exception(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_ping(self, payload: dict):
        """
        Ping an existing Elastic instance
        """
        try:
            elastic_instance_service: ElasticInstanceService = ElasticInstanceService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            success, message = elastic_instance_service.ping_instance(payload["instance"])
            if success:
                return self.response("Successfully pinged Elasticsearch", http.client.OK)
            else:
                return self.response(message, http.client.BAD_REQUEST)
        except ElasticConnectionException as e:
            return self.response(str(e), http.client.BAD_REQUEST)
        except ElasticApplicationException as e:
            return self.response(str(e), http.client.BAD_REQUEST)
        except Exception as e:
            self.logger.exception(traceback.format_exc())
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
        elif exception_string.startswith("Invalid Configuration"):
            return self.response(exception_string.replace("Invalid Configuration: ", ""), http.client.BAD_REQUEST)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
