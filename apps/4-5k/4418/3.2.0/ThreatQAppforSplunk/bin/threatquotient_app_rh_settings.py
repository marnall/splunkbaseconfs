
import traceback
import requests
import threatquotient_app_declare
import json
import base64
import os
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
import splunk.rest

from six.moves.urllib.parse import urlparse
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.splunkenv import get_splunkd_uri
from requests.compat import quote_plus
from six.moves.urllib.parse import quote
from solnlib.utils import is_true
from splunk_aoblib.rest_helper import TARestHelper
import logger_manager as log
from solnlib.utils import is_true
import threatq_utils as utility
from requests.compat import quote_plus
from threatquotient_setup_utils import write_to_conf_file
from threatquotient_setup import  MacroConfiguration, SightingEventConfiguration, EnableSavedSearch, MatchType, DataModel, CustomDataModel, ConsumeAttributes, ConsumeFields, ConsumeSplunkFields, parse_indexes_from_macro
from threatq_const import VERIFY_SSL, VERIFY_SSL_KVSTORE, VERIFY_SSL_FORWARDER, CERT_FILE_LOC, KEY_FILE_LOC
from requests.auth import HTTPBasicAuth

util.remove_http_proxy_env_vars()

INDEXES_MACRO_NAME = "threatq_match_indices"
SETTINGS_CONF_FILE = "threatquotient_app_settings"
STANZA_NAME = "match_algo_detail"
APP_NAME = "ThreatQAppforSplunk"

logger = log.setup_logging("threatquotient_app_rh_settings")
 

class SessionKeyProvider(ConfigMigrationHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class Account(validator.Validator):
    def __init__(self):
        super(Account, self).__init__()
        self.put_msg(
            'Not able to authenticate using provided configuration parameters')

    def _get_proxy_password(self, session_key, app_name, splunkd_uri):
        password = ''
        try:
            splunkd_info = urlparse(splunkd_uri)
            manager = CredentialManager(
                session_key,
                app=app_name,
                realm='__REST_CREDENTIAL__#{0}#{1}'.format(
                    app_name, 'configs/conf-threatquotient_app_settings'),
                scheme=splunkd_info.scheme,
                host=splunkd_info.hostname,
                port=splunkd_info.port
            )
            password = json.loads(manager.get_password(
                'proxy')).get('proxy_password')
        except CredentialNotExistException:
            pass
        return password

    def _get_proxy_settings(self):
        app_name = __file__.split(os.sep)[-3]
        splunkd_uri = get_splunkd_uri()
        rest_endpoint = splunkd_uri + '/servicesNS/nobody/' + \
            app_name + '/threatquotient_app_settings/proxy'
        session_key = SessionKeyProvider().session_key
        params = {"output_mode": "json"}
        
        headers = {
            "Authorization": "Splunk {}".format(session_key),
            "Content-Type": "application/json",
        }
        content = requests.get(
            rest_endpoint,
            headers=headers,
            params=params,
            verify=VERIFY_SSL_KVSTORE
        )
        proxy_settings = content.json()['entry'][0]['content']
        if proxy_settings.get('proxy_username'):
            proxy_settings['proxy_password'] = self._get_proxy_password(
                session_key, app_name, splunkd_uri)
        return proxy_settings

    def _get_proxy_uri(self):
        uri = None
        proxy = self._get_proxy_settings()

        def get_bool(x): return True if x and not x.lower() in [
            '0', 'false', 'f'] else False

        if proxy and get_bool(proxy.get('proxy_enabled')) and proxy.get('proxy_url') and proxy.get('proxy_type'):
            uri = proxy['proxy_url']
            if proxy.get('proxy_port'):
                uri = '{0}:{1}'.format(uri, proxy.get('proxy_port'))
            if proxy.get('proxy_username') and proxy.get('proxy_password'):
                uri = '{0}://{1}:{2}@{3}/'.format(proxy['proxy_type'], quote_plus(proxy[
                    'proxy_username'], safe=""), quote_plus(proxy['proxy_password'], safe=""), uri)
            else:
                uri = '{0}://{1}'.format(proxy['proxy_type'], uri)
        return {"http": uri, "https": uri}

    def _get_access_token(self, data):
        auth_type = data.get('authorization_type', 'basic_auth')

        server_url = data.get('server_url')
        if not server_url:
            return False
        server_url = server_url.strip('/')

        client_id = data.get('client_id')
        if not client_id:
            return False

        if auth_type == "basic_auth":
            username = data.get('username')
            if not username:
                self.put_msg("Username is required")
                return False

            password = data.get('password')
            if not password:
                self.put_msg("Password is required")
                return False
        elif auth_type == "oauth":
            client_secret = data.get("client_secret")
            if not client_secret:
                self.put_msg("Client Secret is required")
                return False

        verify_cert = VERIFY_SSL
        verify_cert = is_true(verify_cert)

        endpoint = '/api/token'
        request_url = '{scheme}{url}{endpoint}'.format(
            scheme='https://', url=server_url, endpoint=endpoint)
        CERT_FILES = None

        if auth_type == "basic_auth":
            request_data = {
                'email': username,
                'password': password,
                'grant_type': 'password',
                'client_id': client_id
            }
            headers = {
                'Content-Type': 'application/json'
            }
            request_data = json.dumps(request_data)
        elif auth_type == "oauth":
            request_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            auth_str = f"{client_id}:{client_secret}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }

        elif auth_type == "cac_auth":
            try:
                def save_cert_file(content, file_path, logger):
                    cert_dir = os.path.dirname(file_path)
                    if not os.path.exists(cert_dir):
                        os.makedirs(cert_dir, exist_ok=True)
                        logger.debug("Created certificate directory at {}.".format(cert_dir))

                    # Write the certificate file
                    with open(file_path, 'w') as f:
                        f.write(content)
                    logger.debug("Wrote certificate file to %s.", file_path)
                    return file_path

                logger.info("Started Validating the configurations")
                headers = {
                    'Content-Type': 'application/json'
                }

                cert_content = data.get("cert_file")
                key_content = data.get("key_file")
                if not cert_content or not key_content:
                    logger.error("message=get_access_token_error |"
                                " Missing certificate or key content")
                    self.put_msg("Please provide both certificate and key content")
                    return False
                cert_file_loc = save_cert_file(cert_content, CERT_FILE_LOC, logger)
                key_file_loc = save_cert_file(key_content, KEY_FILE_LOC, logger)

                CERT_FILES = (cert_file_loc, key_file_loc)
                request_data = {"grant_type": "ssl_certificate", "client_id": client_id}
            except Exception as e:
                logger.error(traceback.format_exc())
                self.put_msg("An error occured. {}".format(str(e)))
                return False

        try:
            logger.info("Started Validating the configurations")
            if auth_type == "cac_auth":
                response = requests.request(
                    "POST", 
                    request_url, 
                    cert=CERT_FILES, 
                    data=request_data, 
                    proxies=self._get_proxy_uri(), 
                    verify=verify_cert
                )
            else:
                response = requests.request(
                    "POST", 
                    request_url, 
                    headers=headers, 
                    data=request_data, 
                    proxies=self._get_proxy_uri(), 
                    verify=verify_cert
                )
            logger.info("Configurations validated successfully.")

        except Exception as e:
            logger.error(traceback.format_exc())
            self.put_msg("An error occured. {}".format(str(e)))
            return False

        # If response is not success
        if response.status_code != 200:
            return False

        try:
            response = response.json()
        except Exception as e:
            logger.error(traceback.format_exc())
            self.put_msg("An error occured. {}".format(str(e)))
            return False

        return True

    def validate(self, value, data):
        return self._get_access_token(data)

class SplunkForwarderConfig(validator.Validator):
    def __init__(self):
        super(SplunkForwarderConfig, self).__init__()

    def validate_forwarder_configuration(self, data):
        try:
            splunkserver = (
                data.get('splunk_forwarder_url', '').strip() or 'localhost'
            )
            if (splunkserver not in ["127.0.0.1", "localhost"] or data.get('splunk_forwarder_password', '').strip() or data.get('splunk_forwarder_username', '').strip()):
                logger.info("validating_details | Validating Forwarder details.")
                payload = 'username={}&password={}'.format(quote_plus(data.get('splunk_forwarder_username', '').strip()), quote_plus(data.get("splunk_forwarder_password", "").strip()))
                splunk_server_port = data.get('splunk_forwarder_port', "").strip() or '8089'
                splunk_verify_cert =  is_true(VERIFY_SSL_FORWARDER)
                if splunkserver in ["127.0.0.1", "localhost"]:
                    splunk_verify_cert = False
                splunk_url = "".join(
                    [
                        "https://",
                        splunkserver,
                        ":",
                        splunk_server_port,
                        "/services/auth/login",
                    ]
                )

                forwarder_proxy_enabled = data.get("forwarder_proxy_enabled", "").strip()
                forwarder_proxy_url = data.get("forwarder_proxy_url", "").strip()
                forwarder_proxy_type = data.get("forwarder_proxy_type", "").strip()
                forwarder_proxy_port = data.get("forwarder_proxy_port", "").strip()
                forwarder_proxy_username = data.get("forwarder_proxy_username", "").strip()
                forwarder_proxy_password = data.get("forwarder_proxy_password", "").strip()
                proxy_data = None
                if all(
                    [
                        is_true(forwarder_proxy_enabled),
                        forwarder_proxy_url,
                        forwarder_proxy_type,
                    ]
                ):
                    http_uri = forwarder_proxy_url
                    if forwarder_proxy_port:
                        http_uri = "{}:{}".format(http_uri, forwarder_proxy_port)
                    if forwarder_proxy_username and forwarder_proxy_password:
                        http_uri = "{}:{}@{}".format(
                            quote(forwarder_proxy_username, safe=""),
                            quote(forwarder_proxy_password, safe=""),
                            http_uri,
                        )
                    http_uri = "{}://{}".format(forwarder_proxy_type, http_uri)
                    proxy_data = {"http": http_uri, "https": http_uri}

                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                response = requests.post(
                    splunk_url,
                    headers=headers,
                    data=payload,
                    verify=splunk_verify_cert,
                    proxies=proxy_data
                )
                if response.status_code == 401:
                    if "incorrect_username_or_password" in response.text:
                        logger.error("Error: Invalid Username or Password. Please make sure provided user({}) exists and password is correct.".format(data.get('splunk_forwarder_username')))
                        self.put_msg("Error: Invalid Username or Password. Please make sure provided user({}) exists and password is correct.".format(data.get('splunk_forwarder_username')))
                        return False
                    logger.error("Please verify the provided configuration.")
                    self.put_msg("Please verify the provided configuration.")
                    return False
                if not response.status_code == requests.codes.ok:
                    self.put_msg("Error occurred while saving the configuration. check splunkd.log")
                    return False

                auth_url = "https://{}:{}/services/authentication/users/{}?output_mode=json".format(splunkserver, splunk_server_port, data.get('splunk_forwarder_username', '').strip())
                auth_response = requests.get(auth_url, verify=splunk_verify_cert, auth=HTTPBasicAuth(data.get('splunk_forwarder_username', '').strip(), data.get('splunk_forwarder_password', '').strip()))
                if auth_response.status_code == 200:
                    user_data = auth_response.json()
                    roles_list = user_data.get("entry")[0]["content"]["capabilities"]
                    if "admin_all_objects" not in roles_list:
                        logger.error("permissions_error | Error: The user({}) having Forwarder machine is missing admin_all_objects capability.".format(data.get('splunk_forwarder_username', '').strip()))
                        self.put_msg("Error: The user({}) having Forwarder machine is missing admin_all_objects capability.".format(data.get('splunk_forwarder_username', '').strip()))
                        return False
                if not auth_response.status_code == requests.codes.ok:
                    logger.error("error_fetching_user_details | Error in fetching user roles. Response: {}".format(auth_response.text))
                logger.info("validation_success | Forwarder details validated successfully.")

        except requests.exceptions.SSLError:
            self.put_msg("Please verify the SSL certificate for the provided configuration.")
            logger.error(traceback.format_exc())
            return False
        except Exception:
            self.put_msg("Please verify the provided configurations.")
            logger.error(traceback.format_exc())
            return False
        return True

    def validate(self, value, data):
        return self.validate_forwarder_configuration(data)

class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """
    def handleList(self, conf_info):
        """Handle list method."""
        logger.debug(
            "message=handle_list_method | handleList called")
        session_key = SessionKeyProvider().session_key
        try:
            indexes = parse_indexes_from_macro(session_key)
        except Exception as err:
            logger.exception(err)
            indexes = ""
        logger.info("message=handle_list_method | Writing indexes to threatquotient_app_settings.conf")
        data = {"indexes": ",".join(indexes)}
        write_to_conf_file(
            SETTINGS_CONF_FILE, STANZA_NAME, data
        )
        settings_conf_file = utility.get_conf_file(session_key, APP_NAME, "threatquotient_app_settings")
        dm_list = settings_conf_file.get("match_algo_detail").get("datamodel_list")
        dm_dict = {"selected_datamodel": dm_list}
        write_to_conf_file(
            SETTINGS_CONF_FILE, "custom_splunk_fields", dm_dict
        )
        type_of_match = {"match_type_custom_fields": settings_conf_file.get("match_algo_detail").get("match_type")}
        write_to_conf_file(
            SETTINGS_CONF_FILE, "custom_splunk_fields", type_of_match
        )
        logger.info("message=handle_list_method | Completed writing indexes to threatquotient_app_settings.conf")
        super(CustomConfigMigrationHandler, self).handleList(conf_info)


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_match_algo_detail = [
    field.RestField(
        'hostname',
        required=True,
        encrypted=False,
        default='Splunk',
        validator=validator.Pattern(
            regex="^[0-9a-zA-Z][0-9a-zA-Z_-]*$|^\*$",
        )    ), 
    field.RestField(
        'indexes',
        required=False,
        encrypted=False,
        default='',
        validator=MacroConfiguration()
    ), 
    field.RestField(
        'sighting_event_configuration',
        required=False,
        encrypted=False,
        default='threatq_consume_indicators',
        validator=SightingEventConfiguration()
    ), 
    field.RestField(
        'enable_es_savedsearches',
        required=False,
        encrypted=False,
        default=False,
        validator=EnableSavedSearch()
    ),
    field.RestField(
        'match_type',
        required=False,
        encrypted=False,
        default=False,
        validator=MatchType()
    ),  
    field.RestField(
        'send_raw_checkbox',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'regex_matching_checkbox',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'partial_matching_checkbox',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'datamodel_list',
        required=False,
        encrypted=False,
        validator=DataModel()
    ),
    field.RestField(
        'custom_dm_matching',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ),
    field.RestField(
        'custom_datamodels',
        required=False,
        encrypted=False,
        default='',
        validator=CustomDataModel()
    ),
    field.RestField(
        'custom_dm_match_fields',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ),
    field.RestField(
        'custom_attributes',
        required=False,
        encrypted=False,
        default='',
        validator=ConsumeAttributes()
    ), 
    field.RestField(
        'custom_fields',
        required=False,
        encrypted=False,
        default='',
        validator=ConsumeFields()
    )
]
model_match_algo_detail = RestModel(fields_match_algo_detail, name='match_algo_detail')

fields_custom_splunk_fields = [
    field.RestField(
        'match_type_custom_fields',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'index_to_consider',
        required=False,
        encrypted=False,
        validator=None
    ),
    field.RestField(
        'selected_datamodel',
        required=False,
        encrypted=False,
        validator=None
    ),
    field.RestField(
        'splunk_additional_fields',
        required=False,
        encrypted=False,
        default='',
        validator=ConsumeSplunkFields()
    )]
model_custom_splunk_fields = RestModel(fields_custom_splunk_fields, name='custom_splunk_fields')

fields_import_timeout = [
    field.RestField(
        'timeout_value',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=9999,
            min_val=300,
        ))
]
model_import_timeout = RestModel(fields_import_timeout, name='import_timeout')

fields_additional_parameters = [
    field.RestField(
        'authorization_type',
        required=True,
        encrypted=False,
        default='basic_auth',
        validator=None
    ),
    field.RestField(
        'username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200,
        )
    ),
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'client_secret',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'server_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        )
    ),
    field.RestField(
        'threatq_splunk_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex="^([\w\.\-]+)$",
        )
    ),
    field.RestField(
        'include_port',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=Account()
    ),
    field.RestField(
        'cert_file',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'key_file',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')

fields_splunk_forwarder_config = [
    field.RestField(
        'splunk_forwarder_username',
        required=False,
        encrypted=False,
        default=None,
        validator=SplunkForwarderConfig()
    ),
    field.RestField(
        'splunk_forwarder_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        )
    ),
    field.RestField(
        'splunk_forwarder_url',
        required=False,
        encrypted=False,
        default="localhost",
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        )
    ),
    field.RestField(
        'splunk_forwarder_port',
        required=False,
        encrypted=False,
        default=8089,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    ),
    field.RestField(
        'forwarder_proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'forwarder_proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'forwarder_proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ), 
    field.RestField(
        'forwarder_proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'forwarder_proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'forwarder_proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_splunk_forwarder_config = RestModel(fields_splunk_forwarder_config, name="splunk_forwarder_config")

endpoint = MultipleModel(
    'threatquotient_app_settings',
    models=[
        model_proxy, 
        model_logging,
        model_import_timeout,
        model_additional_parameters,
        model_match_algo_detail,
        model_custom_splunk_fields,
        model_splunk_forwarder_config
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
