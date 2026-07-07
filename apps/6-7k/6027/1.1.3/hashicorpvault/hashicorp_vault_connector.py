# File: hashicorp_vault_connector.py
#
# Copyright (c) 2020-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import json
import os
import sys
import urllib.parse

import hvac
import phantom.app as phantom
from phantom.action_result import ActionResult

from hashicorp_vault_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class AppConnectorHashicorpVault(phantom.BaseConnector):
    def __init__(self):
        super().__init__()
        return

    def initialize(self):
        self._state = self.load_state()

        if not isinstance(self._state, dict):
            self.debug_print("Resetting the state file with the default format")
            self._state = {"app_version": self.get_app_json().get("app_version")}
            return self.set_status(phantom.APP_ERROR, HASHICORP_VAULT_STATE_FILE_CORRUPT_ERR)

        self._proxies = {}
        if "HTTP_PROXY" in os.environ:
            self._proxies["http"] = os.environ.get("HTTP_PROXY")

        if "HTTPS_PROXY" in os.environ:
            self._proxies["https"] = os.environ.get("HTTPS_PROXY")

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def _get_error_message_from_exception(self, e):
        """
        Get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """

        error_code = None
        error_msg = ERR_MSG_UNAVAILABLE

        try:
            if hasattr(e, "args"):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_msg = e.args[0]
        except:
            pass

        if not error_code:
            error_text = f"Error Message: {error_msg}"
        else:
            error_text = f"Error Code: {error_code}. Error Message: {error_msg}"

        return error_text

    def _get_mountpoint(self):
        self.save_progress("Getting vault mountpoint from asset configuration..._get_mountpoint()")
        config = self.get_config()
        mountpoint = config["vault_mountpoint"]
        return mountpoint

    def _create_vault_client(self, action_result):
        config = self.get_config()

        url = config["vault_url"]
        namespace = config.get("vault_namespace")
        token = config.get("vault_token")
        role_id = config.get("vault_role_id")
        secret_id = config.get("vault_secret_id")
        verify = config.get("verify_server_cert", True)

        try:
            if token:
                vault_client = hvac.Client(url=url, namespace=namespace, verify=verify, token=token, proxies=self._proxies)
            elif role_id and secret_id:
                if namespace:
                    vault_client = hvac.Client(url=url, namespace=namespace, verify=verify, proxies=self._proxies)
                    vault_client.auth.approle.login(role_id=role_id, secret_id=secret_id)
                else:
                    raise ValueError("Namespace must be set in the asset configuration when using AppRole authentication")
            else:
                raise ValueError("Failure while loading asset configuration. Please check your asset configuration.")

            return RetVal(action_result.set_status(phantom.APP_SUCCESS, "Successfully created Hashicorp Vault Client"), vault_client)
        except Exception as e:
            err = urllib.parse.unquote(str(e))
            return RetVal(action_result.set_status(phantom.APP_ERROR, f"Error in getting the Hashicorp Vault Client. {err}"), None)

    def _test_connectivity(self, action_result):
        ret_val, hvac_client = self._create_vault_client(action_result)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if hvac_client:
            try:
                is_authenticated = hvac_client.is_authenticated()
                if is_authenticated:
                    self.save_progress("Successfully connected to Hashicorp vault with given credentials")
                    return action_result.set_status(phantom.APP_SUCCESS, "Successfully connected to Hashicorp Vault")
                else:
                    self.save_progress("Failed to connect to Hashicorp vault with given credentials")
                    return action_result.set_status(phantom.APP_ERROR, "Failed to connect to Hashicorp Vault")
            except Exception as e:
                err = urllib.parse.unquote(str(e))
                return action_result.set_status(phantom.APP_ERROR, f"Error in authenticating Hashicorp Vault Client. {err}")
        else:
            self.save_progress("Failed to create Hashicorp Vault client")
            return action_result.set_status(phantom.APP_ERROR, "Failed to create Hashicorp Vault client")

    def _set_secret(self, param, action_result):
        ret_val, hvac_client = self._create_vault_client(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        mountpoint = self._get_mountpoint()
        path = param.get("location")
        secret = param.get("secret_json")
        try:
            secret = json.loads(secret)
            try:
                create_response = hvac_client.secrets.kv.v2.create_or_update_secret(mount_point=mountpoint, path=path, secret=secret)
                if create_response:
                    self.save_progress("Successfully added the secret")
                    action_result.add_data({"succeeded": True})
                    return action_result.set_status(phantom.APP_SUCCESS, "Successfully added the secret")
                else:
                    self.save_progress("Failed to add the secret to Hashicorp Vault")
                    return action_result.set_status(phantom.APP_ERROR, "Failed to add the secret to Hashicorp Vault")
            except Exception as e:
                err = urllib.parse.unquote(str(e))
                self.save_progress(f"Error occurred while storing the secret in Hashicorp vault. {err}")
                return action_result.set_status(phantom.APP_ERROR, f"Error occurred while storing the secret in Hashicorp vault. {err}")

        except Exception as e:
            err = self._get_error_message_from_exception(e)
            self.save_progress(f"Please verify 'secret_json' action parameter. {err}")
            return action_result.set_status(phantom.APP_ERROR, f"Please verify 'secret_json' action parameter. {err}")

    def _get_secret(self, param, action_result):
        ret_val, hvac_client = self._create_vault_client(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        mountpoint = self._get_mountpoint()
        path = param.get("location")
        try:
            read_response = hvac_client.secrets.kv.v2.read_secret_version(mount_point=mountpoint, path=path)
            if read_response:
                try:
                    secret_value = read_response["data"]["data"]
                    if secret_value:
                        self.save_progress("Secret value retrieved successfully")
                        action_result.add_data({"succeeded": True, "secret_value": secret_value})
                        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved secret value")
                    else:
                        self.save_progress("No secret value retrieved from Hashicorp Vault for the specified path")
                        return action_result.set_status(
                            phantom.APP_ERROR, "No secret value retrieved from Hashicorp Vault for the specified path"
                        )
                except Exception as e:
                    err = self._get_error_message_from_exception(e)
                    return action_result.set_status(phantom.APP_ERROR, f"Error in getting secret value from the API response. {err}")
            else:
                self.save_progress("Error in retrieving secret value from Hashicorp Vault")
                return action_result.set_status(phantom.APP_ERROR, "Error in retrieving secret value from Hashicorp Vault")
        except Exception as e:
            err = urllib.parse.unquote(str(e))
            self.save_progress(f"Error in retrieving secret value from Hashicorp Vault. {err}")
            return action_result.set_status(phantom.APP_ERROR, f"Error in retrieving secret value from Hashicorp Vault. {err}")

    def _list_secrets(self, param, action_result):
        ret_val, hvac_client = self._create_vault_client(action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        mountpoint = self._get_mountpoint()
        path = param.get("location")
        try:
            list_secrets = hvac_client.secrets.kv.v2.list_secrets(mount_point=mountpoint, path=path)
            if list_secrets:
                try:
                    secrets = list_secrets["data"]["keys"]
                    if secrets:
                        self.save_progress("Secrets retrieved successfully")
                        action_result.add_data({"succeeded": True, "secret_values": secrets})
                        return action_result.set_status(phantom.APP_SUCCESS, "Successfully retrieved secret values")
                    else:
                        self.save_progress("No secrets retrieved from Hashicorp Vault for the specified path")
                        return action_result.set_status(phantom.APP_ERROR, "No secrets retrieved from Hashicorp Vault for the specified path")
                except Exception as e:
                    err = self._get_error_message_from_exception(e)
                    return action_result.set_status(phantom.APP_ERROR, f"Error in getting secrets from the API response. {err}")
            else:
                self.save_progress("Error in retrieving secrets from Hashicorp Vault")
                return action_result.set_status(phantom.APP_ERROR, "Error in retrieving secrets from Hashicorp Vault")
        except Exception as e:
            err = urllib.parse.unquote(str(e))
            self.save_progress(f"Error in retrieving secrets from Hashicorp Vault. {err}")
            return action_result.set_status(phantom.APP_ERROR, f"Error in retrieving secrets from Hashicorp Vault. {err}")

    def handle_action(self, param):
        action = self.get_action_identifier()
        action_result = self.add_action_result(ActionResult(dict(param)))

        ret_val = phantom.APP_SUCCESS

        if action == ACTION_ID_SET_SECRET:
            ret_val = self._set_secret(param, action_result)

        if action == ACTION_ID_GET_SECRET:
            ret_val = self._get_secret(param, action_result)

        if action == ACTION_ID_LIST_SECRETS:
            ret_val = self._list_secrets(param, action_result)

        if action == ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(action_result)

        return ret_val


if __name__ == "__main__":
    import pudb

    pudb.set_trace()
    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)
    with open(sys.argv[1]) as (f):
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))
        connector = AppConnectorHashicorpVault()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))
    sys.exit(0)
