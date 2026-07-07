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
    logger = logging.getLogger('splunk.rest.trellix_saas_campaign_details')
    logger.propagate = False
    logger.setLevel(level)
    log_file = make_splunkhome_path(['var', 'log', 'splunk', 'trellix_saas_test.log'])
    file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)
rest_helper = TARestHelper(logger)

class TrellixSaaSCampaignDetails(PersistentServerConnectionApplication):

    def __init__(self, _command_line, _command_arg):
        self.rest_helper = TARestHelper(logger)
        self.server_config_info = {
            'valid_cred': False,
            'device_id': True # Defaulting to True if checking campaign details
        }
        self.server_proxy_info = {}
        self.client_scope_insight = "ins.ms.r ins.suser ins.user "

    def handle(self, in_string):
        try:
            request_info = json.loads(in_string)
            path = request_info.get('rest_path', '') or request_info.get('path', '')
            query_params = dict(request_info.get('query', []))
            session_key = request_info.get('session', {}).get('authtoken')

            self.admin_client = client.connect(token=session_key, autologin=True)
            campaign_id = query_params.get('campaignId', '')

            self.getProxyDetails()
            self.getClearPassword()

            # --- Helper to standardize output ---
            def finalize_response(payload_data, status_code=200):
                return {
                    'payload': json.dumps(payload_data),
                    'status': status_code,
                    'headers': {'Content-Type': 'application/json'}
                }

            logger.debug("campaign_response=")
            # --- VALIDATION BLOCK ---
            if not self.server_config_info.get('client_id'):
                return finalize_response("not_configured")

            if not self.server_config_info.get('valid_cred'):
                token = self.obtain_bearer_token(self.client_scope_insight)
                if not token:
                    return finalize_response("not_valid_cred")
                self.server_config_info['valid_cred'] = True

            # --- ROUTING LOGIC ---
            if "get_campaign" in path:
                res = self.execute_trellix_request(campaign_id, endpoint="")
                return finalize_response(res['payload'].get('data', 'no_campaign'))
            elif "get_galaxies" in path:
                res = self.execute_trellix_request(campaign_id, endpoint="/galaxies", data_type="galaxies")
                return finalize_response(res['payload'].get('data', 'no_campaign'))
            elif "get_ioc" in path:
                res = self.execute_trellix_request(campaign_id, endpoint="/iocs", data_type="iocs")
                return finalize_response(res['payload'].get('data', 'no_campaign'))
            else:
                return {'payload': {"error": "Invalid endpoint", "path": path}, 'status': 400}

            # ... repeat finalize_response pattern for other endpoints ...

        except Exception as e:
            logger.error(f"Trellix: Global Handler Error: {str(e)}")
            return {
                'payload': json.dumps({"error": str(e)}),
                'status': 500,
                'headers': {'Content-Type': 'application/json'}
            }

    def execute_trellix_request(self, campaign_id, endpoint="", data_type="campaign"):
        try:
            auth_token = self.obtain_bearer_token(self.client_scope_insight)
            headers = self.get_header(self.server_config_info.get('api_key'), auth_token)
            url = f"{self.server_config_info['api_gateway_url']}/insights/v2/campaigns/{campaign_id}{endpoint}"

            proxy_uri = self.get_proxy_uri()
            response = rest_helper.send_http_request(url=url, method="GET", headers=headers, timeout=30, proxy_uri=proxy_uri)

            if response and response.status_code == 200:
                resp_json = json.loads(response.text)
                raw_data = resp_json.get("data", [])

                if data_type == "campaign":
                    attr = raw_data.get("attributes", {})
                    result = {
                        "threat_level_id": attr.get("threat-level-id"),
                        "name": attr.get("name"),
                        "description": attr.get("description", "").replace('"', "'"),
                        "links": attr.get("external-analysis", {}).get("links") if attr.get("external-analysis") else []
                    }
                elif data_type == "galaxies":
                    result = [{
                        "id": item.get("id"),
                        "category": item.get("attributes", {}).get("category"),
                        "name": item.get("attributes", {}).get("name"),
                        "description": item.get("attributes", {}).get("description")
                    } for item in raw_data]
                elif data_type == "iocs":
                    result = [{
                        "id": item.get("id"),
                        "category": item.get("attributes", {}).get("category"),
                        "type": item.get("attributes", {}).get("type"),
                        "value": item.get("attributes", {}).get("value"),
                        "lethality": item.get("attributes", {}).get("lethality"),
                        "determinism": item.get("attributes", {}).get("determinism")
                    } for item in raw_data]

                return {'payload': {"data": result}, 'status': 200}

            return {'payload': {"error": "API Error", "status": getattr(response, 'status_code', 'Unknown')}, 'status': 500}

        except Exception as ex:
            return {'payload': {"error": str(ex)}, 'status': 500}

    def getClearPassword(self):
        input_conf_path = make_splunkhome_path(['etc', 'apps', ta_name, 'local', 'inputs.conf'])
        if os.path.exists(input_conf_path):
            input_conf = cli.readConfFile(input_conf_path)
            for name, content in input_conf.items():
                if "trellix_data_source://" in name and content.get('disabled') != '1':
                    self.server_config_info.update({
                        'client_id': content.get('client_id'),
                        'api_gateway_url': content.get('api_gateway_url'),
                        'iam_url': content.get('iam_url')
                    })
                    stanza = name.split('//')[1]
                    for sp in self.admin_client.storage_passwords:
                        if sp.username == f"{stanza}``splunk_cred_sep``1":
                            creds = json.loads(sp.content.clear_password)
                            self.server_config_info.update({
                                'client_secret': creds.get('client_secret'),
                                'api_key': creds.get('api_key')
                            })
                    break

    def getProxyDetails(self):
        proxy_file = make_splunkhome_path(['etc', 'apps', ta_name, 'local', f'{ta_name}_settings.conf'])
        if os.path.exists(proxy_file):
            conf = cli.readConfFile(proxy_file)
            for name, content in conf.items():
                if "proxy" in name and content.get('proxy_enabled') != '0':
                    self.server_proxy_info.update(content)

    def get_proxy_uri(self):
        p = self.server_proxy_info
        if not p.get('proxy_url'): return None
        uri = f"{p['proxy_url']}:{p['proxy_port']}" if p.get('proxy_port') else p['proxy_url']
        return f"{p['proxy_type']}://{uri}"

    def get_header(self, apiKey, token):
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/vnd.api+json', 'x-api-key': apiKey}

    def obtain_bearer_token(self, scope):
        token_url = self.server_config_info.get('iam_url')
        if not token_url: return None
        res = self.get_api_token(scope, token_url)
        if hasattr(res, 'status_code') and res.status_code == 200:
            return json.loads(res.text).get('access_token')
        return None

    def get_api_token(self, scope, token_url):
        try:
            auth_str = f"{self.server_config_info['client_id']}:{self.server_config_info['client_secret']}"
            encoded_auth = base64.b64encode(auth_str.encode("utf-8")).decode('utf-8')
            headers = {'Authorization': f'Basic {encoded_auth}', 'Content-Type': 'application/x-www-form-urlencoded'}
            payload = f"grant_type=client_credentials&scope={scope}"
            return rest_helper.send_http_request(url=token_url, method="POST", payload=payload, headers=headers, timeout=30, proxy_uri=self.get_proxy_uri())
        except Exception as e:
            return None