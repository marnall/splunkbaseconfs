import json

from requests.exceptions import InvalidProxyURL, ProxyError
import splunk.admin as admin
import splunk.entity as entity
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib import conf_manager

# Local library imports
from boxsdk import OAuth2
from boxsdk import Client
from boxsdk import BoxException

from utility import create_session_from_proxy, setup_logger
from ta_box_shield_declare import ta_name as APP_NAME

class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()

class AccountValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        CLIENT_ID = data.get('client_id')
        CLIENT_SECRET = data.get('client_secret')
        ACCESS_TOKEN = data.get('access_token')
        REFRESH_TOKEN = data.get('refresh_token')

        # Default message for the exceptions
        msg = "Please verify all the credentials"
        try:
            logger = setup_logger("ta_box_shield_box_shield_validation")
            session_key = GetSessionKey().session_key
            entities = entity.getEntities(['admin', 'passwords'], namespace=APP_NAME, owner='nobody', sessionKey=session_key, search=APP_NAME, count=0)

            
            conf = conf_manager.ConfManager(session_key, APP_NAME, realm="__REST_CREDENTIAL__#{app_name}#configs/conf-ta_box_shield_settings".format(app_name=APP_NAME))
            config_file = conf.get_conf("ta_box_shield_settings")
            proxy_stanza = config_file.get("proxy", {})

            if proxy_stanza.get("proxy_enabled", 'false').lower() in ['true', '1', 't']:
                if proxy_stanza.get("proxy_username"):
                    # Get the clear proxy password only when proxy is enabled and username is configured
                    for _, value in entities.items():
                        if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                            cred = json.loads(value.get('clear_password','{}'))
                            proxy_password = cred.get('proxy_password', '')
                            break
                    proxy_stanza["proxy_password"] = proxy_password
            else:
                proxy_stanza = {}

            if proxy_stanza:
                session = create_session_from_proxy(proxy_stanza, logger, config=None, helper_log=False)
            else:
                session = None

            oauth = OAuth2(
                    client_id = CLIENT_ID,
                    client_secret = CLIENT_SECRET,
                    access_token = ACCESS_TOKEN,
                    refresh_token = REFRESH_TOKEN,
                    session = session,
                )

            # Use session key to retrieve the proxy stanza from the configuration file
            access_token, refresh_token = oauth.refresh(ACCESS_TOKEN)
            data['access_token'] = access_token
            data['refresh_token'] = refresh_token
            return True
        except InvalidProxyURL as ipu:
            logger.error(
                "Error occurred due to the Invalid URL configured in proxy settings : \nError: {}".format(ipu))
            msg = "Error occurred due to the Invalid URL configured in proxy settings"
        except ProxyError as pe:
            logger.error(
                "Error occurred due to the Proxy configurations : \nError: {}".format(pe))
            msg = "Error occurred due to the Proxy configurations"
        except BoxException as be:
            msg = be.message
            if "client credentials are invalid" in msg:
                msg = "Client ID or Client Secret is Invalid"
            elif "Invalid refresh token" in msg:
                msg = "Refresh Token is Invalid"
            elif "Refresh token has expired" in msg:
                msg = "Refresh Token has expired"
            logger.error(
                "Error occurred while configuring account: Message: {} \nError: {}".format(msg, be))
        except Exception as e:
            logger.error("Error occurred while configuring account: Message: {} \nError: {}".format(msg, e))
        self.put_msg(msg)
        return False