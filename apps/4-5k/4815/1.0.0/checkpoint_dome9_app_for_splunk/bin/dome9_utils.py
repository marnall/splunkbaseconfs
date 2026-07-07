import logging
import json
import sys
from os.path import dirname, abspath, join

new_path = join(dirname(abspath(__file__)), "lib")
sys.path.insert(0, new_path)

import requests
import urllib

import xml.sax.saxutils as xss
import splunk.entity as entity
import splunk.rest as rest
import splunk.admin as admin


TIMEOUT = 120   # 2 min is the default timeout set for all the request being made to dome9 api
APP_NAME = "checkpoint_dome9_app_for_splunk"
STANZA_NAME = "API"
CONF_FILE_NAME = "checkpoint_dome9"
CONNECTION_STANZA_NAME = "connection_params"
EXCLUSION_COLLECTION = "collection_exclusion_list_from_splunk"


def get_credentials(LOGGER, session_key, conf_dict):
    """
    Function returns the API Key and Secret Key in tuple form
    """
    api_key = None
    secret_key = None

    if conf_dict is not None:
        for stanza, settings in conf_dict.items():
            if stanza == STANZA_NAME:
                for key, val in settings.items():
                    if key == "api_key" and val and val != 'None':
                        api_key = val
                break

    if api_key:
        credential_manager = CredentialManager(session_key, LOGGER)
        (_, secret_key) = credential_manager.get_credentials(api_key)
    
    if not api_key or not secret_key:
        api_key = ""
        secret_key = ""
        LOGGER.error("No API key and Secret Key found.")

    return {"api_key": api_key, "secret_key": secret_key}


def get_connection_params(LOGGER, conf_dict):
    """
    Function returns the connection parameters as dictionary.
    """
    base_url = 'https://api.dome9.com/v2'
    ssl_verify = True
    timeout = 120

    if conf_dict  is not None:
        for stanza, settings in conf_dict.items():
            if stanza == CONNECTION_STANZA_NAME:
                for key, val in settings.items():
                    if key == 'base_url' and val and val != 'None':
                        base_url = val.strip('\"')
                    elif key == 'ssl_verify' and val and val != 'None':
                        ssl_verify = convert_to_bool(val)
                    elif key == 'timeout' and val and val != 'None':
                        timeout = float(val)
    return {"base_url": base_url, "ssl_verify": ssl_verify, "timeout": timeout}

def get_proxy_details(LOGGER, session_key, conf_dict):
    cfg =  conf_dict[STANZA_NAME]
    is_proxy_enabled = convert_to_bool(cfg.get('is_proxy_enabled'))
    proxy_ip = xss.unescape(cfg.get('proxy_ip'))
    proxy_port = xss.unescape(cfg.get('proxy_port'))
    proxy_scheme = xss.unescape(cfg.get('proxy_scheme'))
    proxy_is_auth_required = convert_to_bool(cfg.get('proxy_is_auth_required'))
    proxy_username = xss.unescape(cfg.get('proxy_username'))
    credential_manager = CredentialManager(session_key, LOGGER)
    (_, proxy_password) = credential_manager.get_credentials(proxy_username)
    return get_proxy_struct(is_proxy_enabled, proxy_ip, proxy_port, proxy_scheme, proxy_is_auth_required, proxy_username, proxy_password)

def get_proxy_struct(is_proxy_enabled, proxy_ip, proxy_port, proxy_scheme, proxy_is_auth_required, proxy_username, proxy_password):
    proxies = {}
    if is_proxy_enabled:
        proxy_credentials = ""
        if proxy_is_auth_required:
            proxy_credentials = proxy_username + ":" + proxy_password + "@"
        proxy_url = proxy_scheme + "://" + proxy_credentials + proxy_ip + ":" + proxy_port
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    return proxies

def convert_to_bool(string_val):
    """
    Function converts value from string to boolean
    :param: string_val
    :return: converted bool value
    """
    if type(string_val) == bool:
        return string_val

    if isinstance(string_val, basestring):
        if string_val.lower() in ["true", "t", "1", "yes", "y"]:
            return True
        else:
            return False


def cloud_vendor_map(cloud_vendor):
    """
    Function is utility function that converts that value of cloud vendor same API supported value
    :param cloud_vendor: cloud_vendor value from UI table
    :return: converted vendor value
    """
    cloud_vendor = cloud_vendor.lower()
    vendor_map = {
        "aws": "Aws",
        "azure": "Azure",
        "gcp": "Google",
        "kubernetes": "Kubernetes"
    }
    return vendor_map[cloud_vendor]


class Dome9Request(object):
    """
    Class request the Dome9 API and return the response
    """
    def __init__(self, LOGGER, credentials, connection_params, proxies):
        """
        Init for Dome9Request class
        param LOGGER: logger object
        param credentials: api_key and secret_key
        """
        self.LOGGER = LOGGER
        self.credentials = credentials
        self.server = connection_params['base_url']
        self.ssl_verify = connection_params['ssl_verify']
        self.timeout = connection_params['timeout']
        self.proxies = proxies
    
    def request(self, endpoint, method, params=None, body=None):
        """
        Make a request with the help of requests module
        :param endpoint: endpoint (without host and version)
        :param method: HTTP method in string (supported by requests module)
        :param params: request parameters
        :param body: request body
        :return: response
        """
        url = self.server + endpoint
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = json.dumps(body)
        self.LOGGER.debug("Dome9Request - method: {} - url: {} - params: {} - body: {} - headers: {}".format(method, url, params, body, headers))
        try:
            response = requests.request(method, url=url, params=params, data=body, headers=headers,
                 auth=(self.credentials["api_key"], self.credentials["secret_key"]), timeout=self.timeout, verify=self.ssl_verify, proxies=self.proxies)
            return response, None
        except requests.exceptions.ProxyError:
            self.LOGGER.error("Proxy Authentication Failed. Please check your proxy configurations.")
            return None, "Proxy Authentication Failed. Please check your proxy configurations."
        except requests.exceptions.ConnectionError:
            self.LOGGER.error("Proxy Authentication Failed. Please check your proxy configurations.")
            return None, "Proxy Authentication Failed. Please check your proxy configurations."
        except Exception as e:
            self.LOGGER.error(str(e))
            return None, str(e)
    
    def log_content(self, log_level, msg, response):
        """
        Log the content of response (useful when there is any error in response-code)
        """
        self.LOGGER.log(log_level, msg)
        try:
            self.LOGGER.log(log_level, "response:content: " + str(response.content))
            self.LOGGER.log(log_level, "response-json: " + str(response.json()))
        except:
            pass
    

    def handle_error(self, response, call_type):
        """
        Function handles the API errors
        :param response: API response
        :param call_type: type of API call (Exclusion)
        """
        msg = None
        if response.status_code == 401:
            msg = "Status-Code [{}] - {} - Authentication error while calling API, please recheck the API Key and Secret Key.".format(response.status_code, call_type)
        
        if response.status_code >= 500:
            msg = "Status-Code [{}] - {} - Internal server error, please retry after some time.".format(response.status_code, call_type)
        
        if not msg:
            # for cases of client side error
            msg = "Status-Code [{}] - {} - Error occurred while connecting to Dome9 server.".format(response.status_code, call_type)

        self.log_content(logging.ERROR, msg, response)
        return (None, None, msg)



class ValidateAPIKey(Dome9Request):
    """
    Class for validating API Key and other configuration
    """
    def __init__(self, LOGGER, api_key, secret_key, connection_params, proxies):
        """
        Init
        :param LOGGER: logger object
        :param api_key: finding_key
        :param secret_key: secret_key
        """
        credentials = {"api_key": api_key, "secret_key": secret_key}
        super(ValidateAPIKey, self).__init__(LOGGER, credentials, connection_params, proxies)
    
    def validate(self):
        """
        Function to validate whether provided API Key and Secret Key is valid or not
        :return: (success, warning, error)
        """
        response, err_msg = self.request('/CloudAccounts', 'GET')

        if err_msg:
            return(None, None, err_msg)           

        if response.status_code == 200:
            msg = "API key and Secret Key is valid."
            return (msg, None, None)
        
        return self.handle_error(response, "API Key Validation")



class Exclude(Dome9Request):
    """
    Class to create an exclusion on dome9
    """
    def __init__(self, LOGGER, credentials, connection_params, proxies, session_key):
        """
        Init for Exclude
        :param LOGGER: logger object
        :param credentials: api_key and secret_key
        :param collection_params: collection params
        :param proxies: proxy information
        :param session_key: Splunk session key
        """
        super(Exclude, self).__init__(LOGGER, credentials, connection_params, proxies)
        self.session_key = session_key
    
    def exclude(self, rule_logic_hash, entity_id, bundle_id, cloud_account_id, cloud_account_type, comment, finding_key):
        """
        creates an exclusion on dome9
        :param rule_logic_hash: rule logic hash
        :param entity_id: entity id
        :param bundle_id: bundle id
        :param cloud_account_id: cloud account id
        :param cloud_accout_type: cloud account vendor
        :param comment: comment
        :param finding_key: finding key
        :return:  response based on API response
        """
        body = {
            # "ruleName": rule_name,
            # "ruleId": rule_id,
            "bundleId": bundle_id,
            "cloudAccountType": cloud_vendor_map(cloud_account_type),
            "comment": comment
        }
        if rule_logic_hash:
            body["ruleLogicHash"] = rule_logic_hash
        if cloud_account_id:
            body["cloudAccountId"] = cloud_account_id
        if entity_id:
            body["logic"] = "id like '{}'".format(entity_id)

        response, err_msg = self.request('/Exclusion', 'POST', body=body)

        if err_msg:
            return(None, None, err_msg)

        if response.status_code == 201:
            content = response.json()
            msg = "Exclusion created successfully. id={}".format(content["id"])
            KVStoreHandler(self.LOGGER, self.session_key, EXCLUSION_COLLECTION).util_exclusion_created(finding_key)
            return (msg, None, None)

        if response.status_code == 409:
            msg = "The same exclusion logic already exists."
            KVStoreHandler(self.LOGGER, self.session_key, EXCLUSION_COLLECTION).util_exclusion_created(finding_key)
            self.log_content(logging.WARN, msg, response)
            return (None, msg, None)
        
        return self.handle_error(response, "Exclusion")



class CredentialManager:
    '''
    Credential manager to store and retrieve password
    '''
    def __init__(self, session_key, LOGGER):
        '''
        Init for credential manager
        :param session_key: Splunk session key
        :param LOGGER: logger object
        '''
        self.session_key = session_key
        self.LOGGER = LOGGER

    def get_credentials(self, user_name):
        '''
        Searches passwords using username and returns tuple of username and password if credentials are found else tuple of empty string
        :param user_name: Username used to search credentials.
        :return: username, password
        '''
        username = ""
        password = ""
        try:
            # list all credentials
            entities = entity.getEntities(["admin", "passwords"], search=APP_NAME, namespace=APP_NAME, owner="nobody",
                                        sessionKey=self.session_key)

            # return first set of credentials
            for _, value in entities.items():
                if str(value["eai:acl"]["app"]) == APP_NAME and value["username"] == user_name:
                    username = value["username"]
                    password = value["clear_password"]
                    break
        except Exception as e:
            self.LOGGER.exception("Checkpoint Dome9 Splunk App: Could not find any stored credentials. " +
                                    "Please provide your credentials from Splunk -> Manage Apps -> " + APP_NAME + " -> Setup" + str(e))
        return username, password


    def store_password(self, user_name, password):
        '''
        Updates password if password is already stored with given username else create new password.
        :param user_name: Username to be stored.
        :param password: Password to be stored.
        :return: None
        '''
        user, old_password = self.get_credentials(user_name)

        if old_password and user == user_name:
            postargs = {
                "password": password
            }
            user_name = user_name.replace(":", "\:")
            realm = urllib.quote(APP_NAME + ":" + user_name + ":", safe='')
            try:
                rest.simpleRequest(
                    "/servicesNS/nobody/" + APP_NAME + "/storage/passwords/" + realm + "?output_mode=json",
                    self.session_key, postargs=postargs, method='POST', raiseAllErrors=True)

                return True
            except Exception as e:
                self.LOGGER.exception("Checkpoint Dome9 Splunk App: Error occurred while updating the existing credentials. "
                                "Please try again later or contact Splunk Administrator." + str(e))
                raise Exception
        else:
            # when there is no existing password
            postargs = {
                "name": user_name,
                "password": password,
                "realm": APP_NAME
            }
            try:
                rest.simpleRequest("/servicesNS/nobody/" + APP_NAME + "/storage/passwords/?output_mode=json",
                                        self.session_key, postargs=postargs, method='POST', raiseAllErrors=True)
            except Exception as e:
                self.LOGGER.exception("Checkpoint Dome9 Splunk App: Error occurred while storing the new credentials. " +
                                "Please try again later or contact Splunk Administrator." + str(e))
                raise Exception



class KVStoreHandler:
    """
    Class to update KV store lookup
    """
    def __init__(self, LOGGER, session_key, collection):
        """
        Initialize
        :param LOGGER: logger to used
        :param session_key: Splunk session key
        :param collection: Collection to use
        """
        self.LOGGER = LOGGER
        self.session_key = session_key
        self.collection = collection

    def batch_save(self, values):
        """
        Batch save values in the collection
        :param values: values to save in collection
        """
        try:
            rest_endpoint = '/servicesNS/nobody/' + APP_NAME + \
                    '/storage/collections/data/' + self.collection + '/batch_save'
            rest.simpleRequest(rest_endpoint, sessionKey=self.session_key,
                                        method='POST', jsonargs=json.dumps(values), raiseAllErrors=True)
        except Exception as e:
            self.LOGGER.error('Error in Checkpoint Dome9 Exclusion update in lookup:, %s' % str(e))
            raise
    
    def util_exclusion_created(self, finding_key):
        """
        Update collection to add finding_key exclusion created
        """
        change = [{
            "_key": finding_key,
            "findingKey": finding_key,
            "exclude": "1"
        }]
        self.batch_save(change)
