#import debugpy
import json
#Set up remote debugging via debugpy on port 5678
#debugpy.listen(("0.0.0.0", 5678))
#print("Waiting for debugger attach...")
#debugpy.wait_for_client()  # This will pause execution until the debugger is attached

import logging
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth
from splunklib import client
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from constants import INPUTS_METADATA_KV_STORE, CONFIGURATION_NAME, APP_NAME

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Starting tisc_rest_handler.py...")

def validate_instance_connection(account, username, password, url):
    logger.debug(f"Validating instance connection, account: {account}, username: {username}, url: {url}")

    # URL of the endpoint
    api_url = url+'api/sn_sec_tisc/v1/threat_intel_data/observables'

    headers = {
        'Content-Type': 'application/json'
    }

    # Payload
    data = {
        "page_size": "100",
        "page_token": "",
        "included_fields": {
            "observable": {
                "common_fields": {
                    "include_all_fields": False,
                    "values": [
                        "threat_score",
                        "confidence",
                        "threat_level",
                        "reputation",
                        "source_reported_score",
                        "threat_severity"
                    ]
                }
            }
        }
    }

    logger.debug(f"Request body for validating instance connection :{data}")

    # Attempt connection
    try:
        response = requests.post(api_url, headers=headers, json=data, auth=HTTPBasicAuth(username, password))

        # Check if connection is successful
        if response.status_code == 200:
            logger.debug("Validation successful.")
            return True
        else:
            raise ValueError(f"Failed to validate instance. Received response code {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error: {e}")
        raise ValueError("Failed to validate instance due to network issue or invalid URL") from e

class TISCRestHandlerConfig(AdminExternalHandler):

    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleCreate(self, conf_info):
        try:
            logger.debug("Handling create operation for TISC IP config")
            account = str(self.callerArgs.id)
            username =  self.payload.get("username")
            password =  self.payload.get("password")
            instance_Url =  self.payload.get("instanceUrl")
            logger.debug(f"Handling create operation for TISC IP config. Account: {account}, Username: {username}, Instance URL: {instance_Url}")
            validate_instance_connection(account,username,password,instance_Url)
            AdminExternalHandler.handleCreate(self, conf_info)
            logger.debug("Successfully created Instance entry.")
        except Exception as e:
            logger.error(f"Error during handleCreate: {str(e)}")
            raise

    def handleEdit(self, conf_info):
        try:
            logger.debug("Handling edit operation for TISC IP config")
            account = str(self.callerArgs.id)
            username =  self.payload.get("username")
            password =  self.payload.get("password")
            instance_Url =  self.payload.get("instanceUrl")
            logger.debug(f"Handling edit operation for TISC IP config. Account: {account}, Username: {username}, Instance URL: {instance_Url}")
            validate_instance_connection(account, username, password, instance_Url)
            AdminExternalHandler.handleEdit(self, conf_info)
            logger.debug("Successfully edited Instance entry.")
        except Exception as e:
            logger.error(f"Error during handleEdit: {str(e)}")
            raise
    
    def handleRemove(self, conf_info):
        try:
            logger.debug("Handling delete operation for TISC IP config")
            account = str(self.callerArgs.id)

            # Connect to Splunk
            service = client.connect(app=APP_NAME, token=self.getSessionKey())
            kvstore = service.kvstore[INPUTS_METADATA_KV_STORE]

            # Query and delete all metadata records related to this input
            query = {CONFIGURATION_NAME: account}
            records = kvstore.data.query(query=query)

            for record in records:
                query_key=json.dumps({"_key": record['_key']})
                kvstore.data.delete(query_key)

            AdminExternalHandler.handleRemove(self, conf_info)
            logger.debug("Configuration Removed: Successfully deleted configuration entry and related metadata.")

        except Exception as e:
            logger.error(f"Error during handleRemove: {str(e)}")
            raise

    def handleList(self, conf_info):
        admin_external.AdminExternalHandler.handleList(self, conf_info)
