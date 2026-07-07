import ta_precrime_threat_intelligence_declare
import os
import splunk.admin as admin
from splunktaucclib.rest_handler.endpoint.validator import Validator
from api_client import APIClient
import json
import requests
import traceback
import logger_manager as log


logger = log.setup_logging('ta_precrime_server_validation')

class GetSessionKey(admin.MConfigHandler):
    """To get session key."""

    def __init__(self):
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    def __init__(self, *args, **kwargs):
        """
        :param validator: user-defined validating function.
        """
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        try:
            logger.info("Account Validation Success...")
            session_key = GetSessionKey().session_key
            apiclient_object = APIClient(session_key, data)
            logger.info("Account Validation Started...")
            api_url = data["api_url"].rstrip("/")
            username = data["username"]
            password = data["password"]
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            payload= json.dumps({
                "username": username,
                "password": password
            }) 
            response = apiclient_object.api_call_report(api_url + "/" + "user/login", payload, headers)
            if response.status_code == 200:
                res = response.json()
                if res.get("access_token") == False:
                    self.put_msg("Please verify Credentials.")
                    logger.error("Please verify Credentials.")
                    return False
                logger.info("Account Validation Success...")
                logger.info("Account Test Connection Started...")
                access_token = res.get("access_token")
                if access_token:
                    headers = {
                        'accept': 'application/json',
                        'Authorization': f'Bearer {access_token}'
                    }
                    endpoint = api_url + "/" + "test/secure"

                    response = apiclient_object.request_get(endpoint, headers)
                    if response.status_code == 200:
                        logger.info("Account Test Connection Success...")
                        return True
                    else:
                        self.put_msg("Please verify Credentials.")
                        logger.info("Please verify Credentials.")
                        return False
                else:
                    self.put_msg("Please verify Credentials.")
                    logger.error("Please verify Credentials.")
                    return False
            else:
                self.put_msg("There is some issue in API call. please try again later.")
                logger.error("There is some issue in API call. please try again later.")
                return False
        except requests.exceptions.SSLError as e:
            self.put_msg("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False")
            logger.error("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False")
            return False
        except requests.exceptions.ProxyError as e:
            self.put_msg("Please verify Proxy Configurations.")
            logger.error("Please verify Proxy Configurations.")
            return False
        except Exception as e:
            logger.error(
                "Unexpected error occured. "
                "Error trace: {}".format(traceback.format_exc()))
            self.put_msg("Could not connect to PreCrime Account222. Please recheck PreCrime "\
                         "Credentials or Proxy settings. {}".format(e))
            logger.error("Could not connect to PreCrime Account222. Please recheck PreCrime "\
                         "Credentials or Proxy settings. {}".format(e))
            return False
