import requests
import json
from requests.auth import HTTPBasicAuth
from splunktaucclib.rest_handler.endpoint.validator import Validator
from ecs_util import create_proxy_uri_dict


class AccountValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        username = data.get('username')
        password = data.get('password')
        verify_ssl = False if data.get('verify_ssl') == "0" else True

        server_address = data.get('server_address')
        url = "https://{}:4443/login".format(server_address)
        node_url = "https://{}:4443/vdc/nodes".format(server_address)
        headers = {'Accept': 'application/json'}
        try:
            response = requests.request(
                "GET",
                url,
                headers=headers,
                verify=verify_ssl,
                auth=HTTPBasicAuth(username, password),
                proxies=create_proxy_uri_dict(data)
            )
            if response.status_code == 200:
                auth_token = response.headers.get('X-SDS-AUTH-TOKEN')
                version_call_headers = {
                    'Accept': "application/json",
                    'X-SDS-AUTH-TOKEN': auth_token
                }
                version_response = requests.request(
                    "GET", node_url,
                    headers=version_call_headers,
                    verify=verify_ssl,
                    auth=HTTPBasicAuth(username, password),
                    proxies=create_proxy_uri_dict(data)
                )
                if version_response.status_code == 200:
                    version = json.loads(version_response.content)['node'][0]['version']
                    version = ".".join(version.split(".", 4)[:4])
                    data['product_version'] = version
                    return True
                else:
                    message = ""
                    if json.loads(version_response.content)['details']:
                        message = json.loads(version_response.content)['details']
                    self.put_msg("Error in fetching product version: {}.".format(message))
                    return False
            else:
                message = ""
                if json.loads(response.content)['details']:
                    message = json.loads(response.content)['details']
                self.put_msg("Error in connection: {}.".format(message))
                return False
        except requests.exceptions.SSLError:
            self.put_msg(
                "Failed to establish a connection. Please verify SSL certificate.")
            return False
        except Exception:
            self.put_msg(
                "Failed to establish a connection. Please verify Server Address and if proxy is enabled please verify proxy details.")  # noqa: E501
            return False


class ProxyValidator(Validator):
    """Custom proxy validator which extends Validator."""

    def validate(self, value, data):
        """
        Custom proxy validator which checks only for required fields.

        Proxy information will already get validated once we make API call in account validator.
        """
        try:
            if data.get('proxy_enabled', 'false').lower() not in ['0', 'false', 'f']:
                if not data.get('proxy_url'):
                    msg = 'Proxy Host can not be empty'
                    raise Exception(msg)
                elif not data.get('proxy_port'):
                    msg = 'Proxy Port can not be empty'
                    raise Exception(msg)
                elif (data.get('proxy_username') and not data.get('proxy_password')
                      ) or (not data.get('proxy_username') and data.get('proxy_password')):
                    msg = 'Please provide both proxy username and proxy password'
                    raise Exception(msg)
                elif not data.get('proxy_type'):
                    msg = 'Proxy Type can not be empty'
                    raise Exception(msg)
        except Exception as exc:
            self.put_msg(exc)
            return False
        else:
            return True
