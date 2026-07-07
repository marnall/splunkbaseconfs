#!/usr/bin/env python3.7
#
# File: handler_license.py - Version 1.0.4
# Copyright © Datapunctum AG 2024-11-22
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
from s3spl_template.service_license import LicenseService


class LicenseHandler(PersistentServerConnectionApplication, HandlerAbstract):
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
        Fetching licenses from the configuration
        """
        try:
            license_service = LicenseService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            licenses = license_service.get_licenses()

            return self.response(licenses, http.client.OK)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post(self, data: dict):
        """
        Adding / removing licenses
        """
        payload = json.loads(data["payload"])
        action = payload["action"]

        if action == "add":
            return self.handle_post_add(payload)
        elif action == "delete":
            return self.handle_post_delete(payload)
        elif action == "list_for_product_identifier":
            return self.handle_post_for_product_identifier(payload)
        elif action == "list_for_serial":
            return self.handle_post_for_serial(payload)

        return self.response("Invalid action", http.client.BAD_REQUEST)

    def handle_post_add(self, payload: dict):
        """
        Add a license to the configuration
        """
        try:
            license_service = LicenseService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            license = license_service.add_license(payload["license"])

            if license:
                return self.response(license, http.client.OK)
            else:
                return self.response("Failed to add license", http.client.INTERNAL_SERVER_ERROR)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_delete(self, payload: dict):
        """
        Remove a license from the configuration by serial number
        """
        try:
            license_service = LicenseService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            license_service.delete_license(payload["serial"])

            return self.response(payload["serial"], http.client.OK)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_for_product_identifier(self, payload: dict):
        """
        Fetching licenses from the configuration
        """
        try:
            if "product_identifier" not in payload:
                return self.response("Missing product_identifier", http.client.BAD_REQUEST)

            license_service = LicenseService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            licenses = license_service.get_licenses_of_product_identifier(payload["product_identifier"])

            return self.response(licenses, http.client.OK)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def handle_post_for_serial(self, payload: dict):
        """
        Fetching licenses from the configuration
        """
        try:
            if "serial" not in payload:
                return self.response("Missing serial", http.client.BAD_REQUEST)

            license_service = LicenseService(uuid=self.uuid, client=client, session_key=self.session_key, privileged_key=self.privileged_key, user=self.user)
            license = license_service.get_license(payload["serial"])

            if license:
                return self.response(license, http.client.OK)
            else:
                return self.response("License not found", http.client.NOT_FOUND)

        except Exception as e:
            self.logger.error(traceback.format_exc())
            return self.__handle_error(str(e))

    def __handle_error(self, exception_string: str = ""):
        if "not found" in exception_string:
            return self.response("Instance not found", http.client.NOT_FOUND)
        elif "Unauthorized" in exception_string:
            return self.response("Unauthorized", http.client.FORBIDDEN)
        elif "already exists" in exception_string:
            return self.response("License Already Exists", http.client.CONFLICT)
        elif "The current license" in exception_string:
            return self.response(exception_string, http.client.BAD_REQUEST)
        elif exception_string.startswith("Public Exception: "):
            return self.response(exception_string.replace("Public Exception: ", ""), http.client.BAD_REQUEST)
        else:
            return self.response("Failed to handle your request", http.client.INTERNAL_SERVER_ERROR)
