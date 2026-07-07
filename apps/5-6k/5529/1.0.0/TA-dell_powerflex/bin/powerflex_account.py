from splunk import admin
from splunktaucclib.rest_handler.endpoint.validator import Validator

from requests import exceptions

from powerflex_utilities import CredentialManager
from powerflex_utilities import get_logger
from powerflex_utilities import GetSessionKey
from powerflex_utilities import get_accounts
from powerflex_session import PowerFlexSession
from powerflex_session import PowerFlexRequestError


class CustomValidationException(Exception):
    pass

class PowerFlexAccount(object):
    """
    PowerFlex Account
    """
    def __init__(self, name, endpoint, username, password):
        """
        Initialize PowerFlexAccount object
        :param name: Account (System) name
        :param endpoint: The endpoint to connect with the PowerFlex system (ex. https://10.0.1.23:447)
        :param username: username
        :param password: password
        """
        self.name = name
        self.endpoint = str(endpoint).strip(" ").strip("/")
        self.username = str(username).strip(" ")
        self.password = password
        self.session = None
    
    def __str__(self):
        return str(self.name)
    
    def __repr__(self):
        return str(self.name)

    def get_request_session(self, session_key, modinput_helper=None, logger=None):
        """
        Create and returns PowerFlexSession obj (does not create new session obj if already exist)
        """
        if not self.session:
            self.session = PowerFlexSession(account=self, session_key=session_key, modinput_helper=modinput_helper, logger=logger)
        return self.session
    
    def validate(self, session_key, logger):
        """
        Validate current account obj
        """
        try:
            session = self.get_request_session(session_key, logger=logger)
            session.authenticate()
            return True
        except PowerFlexRequestError as e:
            raise e
        except exceptions.Timeout:
            # ReadTimeout or ConnectionTimeout
            raise CustomValidationException("Timeout Error: Verify the IP address or host and try to log in again.")
        except exceptions.ProxyError:
            # Proxy error
            raise CustomValidationException("Proxy Error: Verify proxy configuration and try to log in again.")
        except exceptions.SSLError:
            # Error related to SSL
            raise CustomValidationException("SSL Error: Verify SSL configuration in ta_dell_powerflex_settings.conf and try to log in again.")
        except exceptions.RetryError:
            # Retry error
            raise CustomValidationException("Your attempt to log in was unsuccessful. Please try again.")
        except (exceptions.HTTPError, exceptions.RequestException, Exception):
            # Any other exception
            raise CustomValidationException("An error occurred while requesting for login, please verify all the provided details.")


class PowerFlexAccountValidator(Validator):
    """
    Class to validate input parameters for PowerFlex System
    """   
    def validate(self, value, data):
        """
        Function validates the credential with the use of PowerFlexSession class
        :param value: name of account
        :param data: values related to account
        :return: True in case of validation success
        """
        self.session_key = GetSessionKey().session_key
        endpoint = data['endpoint']
        self.logger = get_logger(self.session_key, 'ta_dell_powerflex_account_validation', "validator")

        account = PowerFlexAccount(endpoint, endpoint, data['username'], data['password'])

        try:
            return account.validate(self.session_key, self.logger)
        except Exception as e:
            self.put_msg(str(e))
            return False
