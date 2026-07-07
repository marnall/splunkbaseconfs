# encoding = utf-8
from __future__ import print_function
import sys
import time
from os.path import dirname, abspath

sys.path.append(dirname(abspath(__file__)))
from datetime import datetime, timezone
from splunk.persistconn.application import PersistentServerConnectionApplication
import import_declare_test
from common import Common
from utils import (
    get_proxy_url_dict,
    send_ui_notification,
    get_conf_stanza_details,
    SSEUtility
)
from typing import Dict, Any
from aws_accounts import AWSAccount
from datetime import datetime as dt

class AutoRotateHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self._ta_name = import_declare_test.ta_name
        self._aws_account_conf_name = "ta_cisco_cloud_security_addon_aws_account"
        self._aws_account_stanza = None
        self.session_token = None
        self.BASE_URL = "https://api.sse.cisco.com"
        self.endpoint = "admin/v2/iam/rotateKey"

    def handle(self, in_string):
        """
        Main handler method for processing incoming requests.
        """
        try:
            params = Common().parse_in_string(in_string)
            self.session_token = params["session"]["authtoken"]
            account_name = params["form"]["name"]
            self._aws_account_stanza = get_conf_stanza_details(session_key=self.session_token, conf_file=self._aws_account_conf_name, stanza_name=account_name)
            try:
                rotated_key_data_response = self._call_rotate_keys(account_name)

                try:
                    self._update_account(account_name, rotated_key_data_response)
                except Exception as update_exc:
                    send_ui_notification(
                        self.session_token,
                        f"Error updating AWS account {account_name} after IAM key rotation. Please Regenerate keys manually.",
                        "error",
                    )
                    return {
                        "payload": {
                            "message": f"Error updating AWS account {account_name} after IAM key rotation: {update_exc}"
                        },
                        "status": 400,
                    }
                send_ui_notification(
                    self.session_token, f"IAM key rotation was performed for the AWS account {account_name}."
                )
                return {
                    "payload": rotated_key_data_response,
                    "status": 200,
                }
            except Exception as rotate_exc:
                send_ui_notification(
                    self.session_token,
                    f"Error during IAM key rotation for the AWS account {account_name}. Please check logs for details.",
                    "error",
                )
                return {
                    "payload": {
                        "message": f"Error during IAM key rotation: {rotate_exc}"
                    },
                    "status": 400,
                }
        except Exception as e:
            return {"payload": {"message": str(e)}, "status": 400}

    def _call_rotate_keys(self, account_name):
        """
        Rotates IAM keys for the specified account if auto-rotation is enabled.
        Args:
            account_name (str): The name of the account for which keys should be rotated.
        Raises:
            Exception: If secure credentials (client_id or client_secret) are not found for the account.
        Returns:
            dict: The result of the IAM key rotation operation.
        """
        client_id, client_secret = self._get_secure_credentials()
        if not client_id or not client_secret:
            raise Exception(
                f"Secure credentials not found for account: {account_name}"
            )
        access_token = self._generate_access_token(client_id, client_secret)
        # Call rotate_iam_key
        rotated_key_data = self._rotate_iam_key_api(self.session_token, access_token)

        return rotated_key_data

    def _update_account(self, account_name, rotate_result):
        """
        Updates the AWS account credentials in the KVStore after IAM key rotation.

        Args:
            account_name (str): The AWS account name.
            rotate_result (dict): The result from the IAM key rotation containing new credentials.

        Raises:
            Exception: If required credentials are missing or update fails.
        """

        # Retrieve currentKeyId and secretAccessKey
        current_key_id = rotate_result.get("currentKeyId")
        secret_access_key = rotate_result.get("secretAccessKey")
        if not current_key_id or not secret_access_key:
            raise Exception(
                "rotate_iam_key did not return currentKeyId or secretAccessKey"
            )
        # Call update() from aws.accounts.py
        account = AWSAccount(account_name, self.session_token)
        time.sleep(15)
        account.update(
            access_key_id=current_key_id,
            secret_access_key=secret_access_key,
            region=account.region,
        )

    def _generate_access_token(self, client_id, client_secret):
        """
        Generates an access token for the current session.

        Returns:
            str: The generated access token.
        """
        try:
            return SSEUtility().generate_access_token(client_id, client_secret)
        except Exception as e:
            raise Exception(f"Failed to generate access token: {str(e)}")

    def _get_secure_credentials(self):
        """
        Retrieves secure credentials for the specified AWS account.

        Args:
            account_name (str): The name of the AWS account.

        Returns:
            dict: The secure credentials for the AWS account.
        """
        try:
            account_fields = self._aws_account_stanza
            return (
                account_fields.get("secure_access_client_id"),
                account_fields.get("secure_access_client_secret"),
            )
        except Exception as e:
            raise Exception(f"Failed to retrieve secure credentials: {str(e)}")

    def _rotate_iam_key_api(self, session_key: str, access_token: str) -> Dict[str, Any]:
        """
        Calls the Cisco SSE Rotate Key API to rotate the IAM key.

        Args:
            session_key (str): The Splunk session key for retrieving proxy settings.
            access_token (str): The access token for authentication.

        Returns:
            Dict[str, Any]: The JSON response from the API.

        Raises:
            Exception: If the API call fails.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.BASE_URL}/{self.endpoint}"
        proxies = get_proxy_url_dict(session_key)
        sse_utility = SSEUtility()
        response_data = sse_utility.make_api_request(url=url, headers=headers, proxies=proxies)
        return response_data
