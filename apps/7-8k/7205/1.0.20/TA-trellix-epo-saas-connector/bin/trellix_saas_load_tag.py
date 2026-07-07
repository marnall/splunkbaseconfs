import os
import sys
import re

if sys.version_info[0] < 3:
    py_version = "aob_py3"
else:
    py_version = "aob_py3"

ta_name = 'TA-trellix-epo-saas-connector'
ta_lib_name = 'ta_trellix_epo_saas_connector'

lib_env_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', ta_name,'bin',ta_lib_name)

#parent_path = Path(os.path.dirname(__file__)).resolve().parents[1]
#bin_path = os.path.sep.join([str(parent_path),"bin\\"+ta_lib_name])

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
#new_paths.insert(0, os.path.sep.join(["C:\\Program Files\\Splunk\\etc\\apps\\TA-trellix-epo-saas-connector\\bin", ta_lib_name, py_version]))
#new_paths.insert(0, os.path.sep.join(["C:\\Program Files\\Splunk\\etc\\apps\\TA-trellix-epo-saas-connector", ta_lib_name]))
new_paths.insert(0, os.path.sep.join([lib_env_path, py_version]))
new_paths.insert(0,lib_env_path)
sys.path = new_paths

import logging
import os
import json
import base64
import requests
import splunklib.client as client
from splunktaucclib.splunk_aoblib.rest_helper import TARestHelper
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib import cli_common as cli
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunktaucclib.splunk_aoblib.rest_helper import TARestHelper

_APPNAME = 'TA-trellix-epo-saas-connector'

# Trellix Scopes
client_scope_device = "epo.device.r epo.device.w "
client_scope_tag = "epo.tags.r epo.tags.w"

def setup_logger(level):
    logger = logging.getLogger('splunk.rest.trellix_saas_load_tag')
    logger.propagate = False
    logger.setLevel(level)
    log_file = make_splunkhome_path(['var', 'log', 'splunk', 'trellix_saas_apply_tag_controller.log'])
    file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)
rest_helper = TARestHelper(logger)


class TrellixSaaSLoadTag(PersistentServerConnectionApplication):

    def __init__(self, _command_line, _command_arg):
        # REMOVE the super() call. Initialize variables directly.
        self.rest_helper = TARestHelper(logger)

    endnode_ip = ""
    agentguid = ""
    server_config_info ={}
    server_proxy_info = {}

    def handle(self, in_string):
        """Main entry point for Persistent REST Handler"""
        try:
            request_info = json.loads(in_string)
            path = request_info.get('rest_path', '') or request_info.get('path', '')
            query_params = dict(request_info.get('query', []))
            session_key = request_info.get('session', {}).get('authtoken')

            # Setup Splunk Client using the token from request
            self.admin_client = client.connect(token=session_key, autologin=True)

            # Extract query parameters
            self.endnode_ip = query_params.get('ip', '')
            self.agentguid = query_params.get('agentguid', '')

            self.server_config_info ={}
            self.getProxyDetails()
            self.getClearPassword()

            logger.debug("AFTER CLEAR="+str(self.server_config_info))

            # Check credentials and device
            if not self.server_config_info.get('client_id'):
                return {'payload': "not_configured", 'status': 200}
            if not self.server_config_info.get('valid_cred'):
                return {'payload': "not_valid_cred", 'status': 200}
            if self.server_config_info.get('limit_reached'):
                return {'payload': "limit_reached", 'status': 200}
            if not self.server_config_info.get('device_id'):
                return {'payload': "no_device", 'status': 200}

            # Routing Logic
            if "load_tags" in path:
                logger.debug("LOAD Tags")
                # Initialize Config and Proxy
                return self.execute_load_tags_logic()
            elif "apply_tags" in path:
                logger.debug("APPLY Tags")
                tag_id = query_params.get('tag_list', '')
                return self.execute_apply_tags_logic(tag_id)
            elif "applied_tags" in path:
                logger.debug("applied_tags")
                return self.execute_applied_tags_logic(self.server_config_info['device_id'])
            elif "remove_tags" in path:
                logger.debug("remove_tags")
                tag_ids = query_params.get('tagids', '')
                return self.execute_remove_tags_logic(tag_ids)
            elif "device_details" in path:
                logger.debug("device_details")
                # Initialize Config and Proxy
                return self.execute_device_details_logic(self.server_config_info['device_id'])
            else:
                return {'payload': {"error": "Invalid endpoint", "received_path": path}, 'status': 400}

        except Exception as e:
            logger.error(f"Trellix: Global Handler Error: {str(e)}")
            return {'payload': {"error": str(e)}, 'status': 500}

    def execute_load_tags_logic(self):
        """Ported logic from get_tags"""
        if not self.endnode_ip or self.endnode_ip.strip() == "":
            return {'payload': "IP Address is invalid", 'status': 400}

        tag_response = self.get_Tag_list()
        logger.debug("tag_response="+str(tag_response.status_code))
        if tag_response.status_code == 200:
            tag_list = json.loads(tag_response.text).get('data', [])
            tag_json = [{"id": t["id"], "Tags": t["attributes"]["name"]} for t in tag_list]
            return {'payload': {"data": tag_json}, 'status': 200}
        elif tag_response.status_code == 429:
            return {'payload': "limit_reached", 'status': 200}
        return {'payload': "error_fetching_tags", 'status': 500}

    def execute_apply_tags_logic(self, tag_id):
        """Ported logic from apply_tags"""
        try:
            if not tag_id:
                return {'payload': "Missing tag_list", 'status': 400}

            tag_payload = {"data": [{"id": int(tag_id), "type": "tags"}]}
            auth_token = self.obtain_bearer_token(client_scope_device + client_scope_tag)

            if auth_token:
                headers = self.get_header(self.server_config_info['api_key'], auth_token)
                url = f"{self.server_config_info['api_gateway_url']}/epo/v2/devices/{self.server_config_info['device_id']}/relationships/assignedTags"

                proxyuri = self.get_proxy_uri() if self.server_proxy_info.get('proxy_url') else None
                response = self.rest_helper.send_http_request(
                    url=url, method="POST", payload=tag_payload, headers=headers, timeout=30, proxy_uri=proxyuri
                )

                if response.status_code == 204:
                    return {'payload': "ApplyTag_OK", 'status': 200}
                elif response.status_code == 422:
                    return {'payload': "ApplyTag_ALREAY_EXIST", 'status': 200}
                return {'payload': "Failed to connect to Trellix API", 'status': 500}
        except Exception as e:
            logger.error(f"Trellix: apply_tags error: {str(e)}")
            return {'payload': str(e), 'status': 500}

    # --- Utility Methods (Copied from your original file) ---
    def get_Tag_list(self):
        auth_token = self.obtain_bearer_token(client_scope_tag)
        headers = self.get_header(self.server_config_info['api_key'], auth_token)
        url = self.server_config_info['api_gateway_url'] + '/epo/v2/tags'
        proxyuri = self.get_proxy_uri() if self.server_proxy_info.get('proxy_url') else None
        return self.rest_helper.send_http_request(url=url, method="GET", headers=headers, timeout=30, proxy_uri=proxyuri)

    def getClearPassword(self):

        input_conf_file_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', _APPNAME, "local", "inputs.conf")

        # ... (rest of your existing getClearPassword logic here) ...
        # Ensure you use self.admin_client.storage_passwords as initialized in handle()
        if os.path.exists(input_conf_file_path):
            input_conf = cli.readConfFile(input_conf_file_path)
            for name, content in input_conf.items():
                if "trellix_data_source://" in name and content.get('disabled') != '1':
                    self.server_config_info['client_id'] = content.get('client_id')
                    self.server_config_info['api_gateway_url'] = content.get('api_gateway_url')
                    self.server_config_info['iam_url'] = content.get('iam_url')
                    # Password logic remains the same
                    for storage_password in self.admin_client.storage_passwords:
                        if storage_password.username == f"{name.split('//')[1]}``splunk_cred_sep``1":
                            creds = json.loads(storage_password.content.clear_password)
                            self.server_config_info['client_secret'] = creds.get('client_secret')
                            self.server_config_info['api_key'] = creds.get('api_key')

                    device_response = self.get_device_list()
                    if hasattr(device_response, 'status_code') and device_response.status_code == 200:
                        json_device = json.loads(device_response.text)
                        if json_device["meta"]["totalResourceCount"] > 0:
                            self.server_config_info['device_id'] = json_device["data"][0]['id']
                    if hasattr(device_response, 'status_code') and device_response.status_code == 429:
                        self.server_config_info['limit_reached'] = "True"
                    break

    def getProxyDetails(self):
        try:
            proxy_config_fileName = "ta_trellix_epo_saas_connector_settings.conf"
            proxy_config_file_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', _APPNAME,"local",proxy_config_fileName)

            self.server_proxy_info['proxy_type'] = ''
            self.server_proxy_info['proxy_url'] = ''
            self.server_proxy_info['proxy_port'] = ''
            self.server_proxy_info['proxy_username'] = ''

            if os.path.exists(proxy_config_file_path):

                proxy_conf = cli.readConfFile(proxy_config_file_path)
                for name, content in proxy_conf.items():
                    logger.debug("ELSE ELSE ELSE=")
                    if "proxy" in name:
                        if(content['proxy_enabled'] != '0'):
                            self.server_proxy_info['proxy_type'] = content['proxy_type']
                            self.server_proxy_info['proxy_url'] = content['proxy_url']
                            self.server_proxy_info['proxy_port'] = content['proxy_port']
                            #self.server_proxy_info['proxy_username'] = content['proxy_username']
            else:
                logger.debug("The proxy config file :" + str(proxy_config_fileName) + "is not valid or not available")
        except Exception as ex:
            logger.debug("Trellix: Error Occurred while getting proxy detials from the configuation file="+str(ex))

    def get_proxy_uri(self):
        uri = None
        if self.server_proxy_info['proxy_url'] and self.server_proxy_info['proxy_type']:
            uri = self.server_proxy_info['proxy_url']
            if self.server_proxy_info['proxy_port']:
                uri = "{}:{}".format(uri, self.server_proxy_info['proxy_port'])
            if self.server_proxy_info['proxy_username'] and self.server_proxy_info['proxy_password']:
                uri = "{}://{}:{}@{}/".format(
                    self.server_proxy_info['proxy_type'],
                    self.server_proxy_info['proxy_username'],
                    self.server_proxy_info['proxy_password'],
                    uri,
                )
            else:
                uri = "{}://{}".format(self.server_proxy_info['proxy_type'], uri)
        return uri

    def get_header(self, apiKey, token):
        HEADERS = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/vnd.api+json',
            'x-api-key': apiKey
        }
        return HEADERS

    def obtain_bearer_token(self, scope):
        logger.debug("Trellix: requesting new token")
        logger.debug("CONFIG="+str(self.server_config_info))

        token_url = self.server_config_info['iam_url']
        res_token = self.get_api_token(scope,token_url)

        if hasattr(res_token, 'status_code') and res_token.status_code == 200:
            token_json = json.loads(res_token.text)
            auth_token = token_json['access_token']

            #expires_in = (10*60) # 9 minutes
            #if 'expires_in' in token_json:
            #    expires_in = token_json['expires_in']

            # Subtract 1 minute to ensure it doesn't expire
            #expires_in -= (1*60)
            #token_expires_at = time.time() + expires_in
            #cached_token = auth_token
            #return cached_token
            return auth_token
        elif (hasattr(res_token, 'status_code') and res_token.status_code == 401) or ("ALTER_IAM"==res_token):
            if "realms" in token_url:
                temp_url = "https://iam.cloud.trellix.com/iam/v1.1/token"
            else:
                temp_url = "https://auth.trellix.com/auth/realms/IAM/protocol/openid-connect/token"

            res_token = self.get_api_token(scope,temp_url)
            logger.info("Trellix: requesting dual IAM token="+str(res_token))

            if hasattr(res_token, 'status_code') and res_token.status_code == 200:
                token_json = json.loads(res_token.text)
                auth_token = token_json['access_token']
                return auth_token

            else:
                #cached_token = None
                auth_token = None
                raise Exception(f"Trellix: Error obtain dual IAM Credentials for the input")
        else:
            #cached_token = None
            auth_token = None
            raise Exception(f"Trellix: Error obtain Credentials for the input")

    def get_device_list(self):
        try:
            auth_token = self.obtain_bearer_token(client_scope_device)
            if(auth_token != None):
                self.server_config_info['valid_cred'] = 'present'
                decrypted_apiKey =self.server_config_info['api_key']
                HEADERS = self.get_header(decrypted_apiKey, auth_token)
                url = self.server_config_info['api_gateway_url'] + '/epo/v2/devices?filter[ipAddress]='+self.endnode_ip+'&filter[agentGuid]='+self.agentguid
                if self.server_proxy_info['proxy_url'] != None :
                    proxyuri = self.get_proxy_uri()
                    response =  rest_helper.send_http_request(
                        url=url,
                        method="GET",
                        headers=HEADERS,
                        timeout=30,
                        proxy_uri=proxyuri
                    )
                else:
                    response =  rest_helper.send_http_request(
                        url=url,
                        method="GET",
                        headers=HEADERS,
                        timeout=30
                    )

                logger.debug("AGENT GUID==="+str(response)+" URL="+str(url))
                return response
            else:
                self.server_config_info['valid_cred'] = ''
                return "no_token_found"

        except Exception as ex:
            logger.debug("Trellix :get_device_list() : Error occurred = "+str(ex))
            return "no_token_found"


    def get_api_token(self,scope,token_url):
        try:
            client_id = self.server_config_info['client_id']
            client_secret = self.server_config_info["client_secret"]
            data_string = str(client_id) + ":" + str(client_secret)
            data_bytes = data_string.encode("utf-8")
            encoded_value = base64.b64encode(data_bytes)

            HEADERS = {
                'Authorization': 'Basic ' + str(encoded_value.decode('utf-8')),
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            parameters="grant_type=client_credentials&scope="+scope

            if self.server_proxy_info['proxy_url'] != None :
                proxyuri = self.get_proxy_uri()
                response = rest_helper.send_http_request(
                    url=token_url,
                    method="POST",
                    payload=parameters,
                    headers=HEADERS,
                    timeout=30,
                    proxy_uri=proxyuri
                )
            else:
                response = rest_helper.send_http_request(
                    url=token_url,
                    method="POST",
                    payload=parameters,
                    headers=HEADERS,
                    timeout=30
                )
            return response

        except requests.ReadTimeout as ex:
            logger.debug("Trellix :get_api_token() MESSAGE : Read Timeout = " + str(ex))
            return "ALTER_IAM"
        except Exception as ex:
            logger.debug("Trellix :get_api_token() : Error Occurred = "+str(ex))
            return ex

    def execute_applied_tags_logic(self, device_id):
        """Ported logic from applied_tags"""
        try:
            if not device_id:
                return {'payload': "Missing device_id", 'status': 400}

            logger.debug("execute_applied_tags_logic")
            auth_token = self.obtain_bearer_token(client_scope_device + client_scope_tag)

            if auth_token:
                headers = self.get_header(self.server_config_info['api_key'], auth_token)
                url = f"{self.server_config_info['api_gateway_url']}/epo/v2/devices/{self.server_config_info['device_id']}/assignedTags"

                proxyuri = self.get_proxy_uri() if self.server_proxy_info.get('proxy_url') else None
                response = self.rest_helper.send_http_request(
                    url=url, method="GET", headers=headers, timeout=30, proxy_uri=proxyuri
                )

                if response.status_code == 200:
                    tag_json = json.loads(response.text)
                    tag_list = tag_json['data']
                    tag_json = [];
                    for id in tag_list:
                        tag_det = id
                        dev_attr = tag_det["attributes"]
                        tag_name = dev_attr["name"]
                        tag_obj = {
                            "id": tag_det["id"], "Tags": tag_name
                        }

                        tag_json.append(tag_obj);

                    logger.debug("execute_applied_tags_logic inside")
                    return {'payload': {"data": tag_json}, 'status': 200}
                elif response.status_code == 429:
                    return {'payload': "limit_reached", 'status': 200}
            else:
                return {'payload': "Failed to connect to Trellix API", 'status': 500}
        except Exception as e:
            logger.error(f"Trellix: execute_applied_tags_logic error: {str(e)}")
            return {'payload': str(e), 'status': 500}

    def execute_remove_tags_logic(self, tag_ids):
        """Ported logic from applied_tags"""
        try:
            if not tag_ids:
                return {'payload': "Missing tags_id", 'status': 400}

            multitag_ids = tag_ids.split(",")
            tag_json = [];
            for id in multitag_ids:
                tag_obj = {
                    "id": int(id), "type": "tags"
                }
                tag_json.append(tag_obj);

            tag_ips = {
                "data": tag_json
            }

            auth_token = self.obtain_bearer_token(client_scope_device + client_scope_tag)

            if auth_token:
                headers = self.get_header(self.server_config_info['api_key'], auth_token)
                url = f"{self.server_config_info['api_gateway_url']}/epo/v2/devices/{self.server_config_info['device_id']}/relationships/assignedTags"

                proxyuri = self.get_proxy_uri() if self.server_proxy_info.get('proxy_url') else None
                response = self.rest_helper.send_http_request(
                    url=url, method="DELETE", payload=tag_ips, headers=headers, timeout=30, proxy_uri=proxyuri
                )

                if response.status_code == 204:
                    return {'payload': "RemoveTag_OK", 'status': 200}
                elif response.status_code == 429:
                    return {'payload': "limit_reached", 'status': 200}
            else:
                return {'payload': "Failed to connect to Trellix API", 'status': 500}
        except Exception as e:
            logger.error(f"Trellix: execute_remove_tags_logic error: {str(e)}")
            return {'payload': str(e), 'status': 500}

    def execute_device_details_logic(self, device_id):
        """Ported logic from applied_tags"""
        try:
            if not device_id:
                return {'payload': "Missing device_id", 'status': 400}

            logger.debug("execute_device_details_logic")
            auth_token = self.obtain_bearer_token(client_scope_device + client_scope_tag)

            if auth_token:
                headers = self.get_header(self.server_config_info['api_key'], auth_token)
                url = self.server_config_info['api_gateway_url'] + '/epo/v2/devices?filter[ipAddress]='+self.endnode_ip+'&filter[agentGuid]='+self.agentguid

                proxyuri = self.get_proxy_uri() if self.server_proxy_info.get('proxy_url') else None
                response = self.rest_helper.send_http_request(
                    url=url, method="GET", headers=headers, timeout=30, proxy_uri=proxyuri
                )
                if(response.status_code !=429):
                    dev_res = json.loads(response.text)
                    if len(dev_res['data']) != 0:
                        dev_list = dev_res['data']
                        product_names =''
                        for device in dev_list:
                            device_id = device['id']
                            res = device['attributes']
                            #res.pop("resortEnabled")
                            #logger.debug("########## DEVICE TAGE###"+str(res))
                            installed_pro_res = self.get_installed_product_details(device_id)
                            #logger.debug(" INSTALLED RESPONSE="+str(installed_pro_res.text))

                            if (installed_pro_res.status_code == 200):
                                logger.debug("INSTALLED PRODUCT RESPONSE="+str(installed_pro_res))
                                product_json = json.loads(installed_pro_res.text)
                                logger.debug("123 JSON="+str(product_json))
                                product_list = product_json['data']
                                for product_data in product_list:
                                    product_attributes = product_data['attributes']
                                    if product_attributes['productFamilyName'] is not None:
                                        if len(product_names) != 0:
                                            product_names +=","
                                        product_names +=product_attributes['productFamilyName']+":"+product_attributes['productVersion']
                            else:
                                product_names = ""

                        final_res = {
                            "response":res,
                            "installed_products":product_names
                        }
                        logger.debug("DEVICE RESPONSE="+str(final_res))
                        return {'payload': {"data": final_res}, 'status': 200}
                else:
                    logger.debug("limit reached")
                    return {'payload': "limit_reached", 'status': 200}
            else:
                return {'payload': "Failed to connect to Trellix API", 'status': 500}
        except Exception as e:
            logger.error(f"Trellix: execute_device_details_logic error: {str(e)}")
            return {'payload': str(e), 'status': 500}

    def get_installed_product_details(self,device_id):
        logger.debug("!!!! get_installed_product_details !!!!!!!")
        try:
            auth_token = self.obtain_bearer_token(client_scope_device)

            if(auth_token != None):
                decrypted_apiKey =self.server_config_info['api_key']
                HEADERS = self.get_header(decrypted_apiKey, auth_token)
                url = self.server_config_info['api_gateway_url'] + '/epo/v2/devices/'+device_id+'/installedProducts'
                #logger.debug("INSTALLED PRODUCT URL="+str(url)+"   HEADERS="+str(HEADERS))
                if self.server_proxy_info['proxy_url'] != None :
                    proxyuri = self.get_proxy_uri()
                    response = self.rest_helper.send_http_request(
                        url=url,
                        method="GET",
                        headers=HEADERS,
                        timeout=30,
                        proxy_uri=proxyuri
                    )
                else:
                    response =  self.rest_helper.send_http_request(
                        url= url,
                        method="GET",
                        headers=HEADERS,
                        timeout=30
                    )
                return response

        except Exception as e:
            logger.debug("Trellix: Error Occurred While get_installed_product_details" + e)