"""Utilities related to account page."""

import sys
import os
import requests
import socks

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "common")))

import ta_netskopeappforsplunk_declare  # noqa: F401

from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint import SingleModel
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.endpoint.validator import Validator
import netskope_utils

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

CONNECTION_STRING_ERROR = "Connection String is required field. Please enter a Connection String."
BAD_REQUEST_STATUS_CODE = 400
MAX_RETRY = 3


def create_blob_service(connection_string, proxies=None):
    """Create an Azure Blob Service Client."""
    return BlobServiceClient.from_connection_string(
        conn_str=connection_string,
        proxies=proxies,
    )


class StorageAccountModel(SingleModel):
    """Account Model."""

    def validate(self, name, data, existing=None):
        """To get stanza name for future use as it can only be retrive from here."""
        # Create the object of class BlobServiceClient
        dest_container_name = data.get("dest_container_name")
        connection_string = data.get("connection_string")

        if dest_container_name is None:
            raise RestError(
                BAD_REQUEST_STATUS_CODE,
                "Destination container name is required field. Please enter the Destination container name.",
            )

        if connection_string is None:
            raise RestError(
                BAD_REQUEST_STATUS_CODE,
                CONNECTION_STRING_ERROR,
            )

        super(StorageAccountModel, self).validate(name, data, existing)


class StorageAccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, conf_info):
        """Handle creation of account in config file."""
        super(StorageAccountHandler, self).handleCreate(conf_info)

    def handleRemove(self, conf_info):
        """Handle the delete operation."""
        super(ConfigMigrationHandler, self).handleRemove(conf_info)


class ConnectionStringValidator(Validator):
    """To Validate Coonection String of Microsoft Storage Account."""

    def validate(self, value, data):
        """Validate Connection String given by user."""
        try:
            connection_string = data.get("connection_string")
            if connection_string is None:
                self.put_msg(
                    CONNECTION_STRING_ERROR
                )
                return False
            _ = create_blob_service(
                data.get("connection_string"),
                proxies=netskope_utils.create_requests_proxy_dict(),
            )
        except (requests.exceptions.ProxyError, socks.ProxyError):
            self.put_msg(
                "Invalid Proxy credentials. Please recheck your Proxy settings."
            )
            return False
        except Exception as ex:
            self.put_msg("Account Validation failed : {}".format(ex))
            return False

        return True


class DestContainerValidator(Validator):
    """To Validate Destination Container's existence."""

    def validate(self, value, data):
        """Validate Destination Container given by user."""
        try:
            dest_container_name = data.get("dest_container_name")
            connection_string = data.get("connection_string")
            if dest_container_name is None:
                self.put_msg(
                    "Destination container name is required field. Please enter the Destination container name."
                )
                return False
            if connection_string is None:
                self.put_msg(
                    CONNECTION_STRING_ERROR
                )
                return False

            blob_service_client = create_blob_service(
                connection_string,
                proxies=netskope_utils.create_requests_proxy_dict(),
            )
            destination_container_client = (
                blob_service_client.get_container_client(dest_container_name)
            )
            _ = destination_container_client.get_container_properties()

        except ResourceNotFoundError:
            self.put_msg(
                "Destination Container does not exist. Please enter a valid container name."
            )
            return False
        except Exception as ex:
            self.put_msg(
                "Destination Container Validation failed : {}".format(ex)
            )
            return False

        return True
