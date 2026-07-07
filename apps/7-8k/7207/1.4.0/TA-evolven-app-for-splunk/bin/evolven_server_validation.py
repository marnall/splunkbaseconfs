import ta_evolven_app_for_splunk_declare
import os
import splunk.admin as admin
from splunktaucclib.rest_handler.endpoint.validator import Validator
import requests
import traceback


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
        url = data["url"].rstrip("/")
        username = data["username"]
        password = data["password"]
        headers = {
            'user': username,
            'pass': password
        }
        try:
            # To call the method for validating the account
            response = requests.get(url + "/" + "enlight.server/next/api?action=login&json=true", headers=headers)
            res = response.json()
            if res.get("Next").get("ID"):
                return True
            else:
                self.put_msg("Please verify Evolven Credentials.")
                return False
        except requests.exceptions.SSLError as e:
            self.put_msg("SSL certificate verification failed. Please add a valid "\
                         "SSL Certificate or Change VERIFY_SSL flag to False")
            return False
        except requests.exceptions.ProxyError as e:
            self.put_msg("Please verify Proxy Configurations.")
            return False
        except Exception as e:
            self.put_msg("Could not connect to Evolven Account. Please recheck Evolven "\
                         "Credentials or Proxy settings. {}".format(e))
            return False
