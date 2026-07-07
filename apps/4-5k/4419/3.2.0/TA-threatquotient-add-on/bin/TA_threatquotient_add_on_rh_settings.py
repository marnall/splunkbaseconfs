
import traceback
import ta_threatquotient_add_on_declare
import json
import os
import base64
from six.moves.urllib.parse import urlparse
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import splunk.rest
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.splunkenv import get_splunkd_uri
from solnlib.utils import is_true
from splunk_aoblib.rest_helper import TARestHelper
import requests
from requests.compat import quote_plus
from threatq_const import VERIFY_SSL, VERIFY_SSL_KVSTORE, CERT_FILE_LOC, KEY_FILE_LOC
import logger_manager as log
logger = log.setup_logging("ta_threatquotient_add_on_rh_settings")

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception as err:
    pass
util.remove_http_proxy_env_vars()

class SessionKeyProvider(ConfigMigrationHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()

class SplunkKvStoreRest(validator.Validator):
    def __init__(self):
        super(SplunkKvStoreRest, self).__init__()

    def validate_splunk_kvstore_rest_credentials(self, data):
        try:
            splunkserver = (
                data.get('splunk_rest_host_url') or 'localhost'
            )
            if (splunkserver not in ["127.0.0.1", "localhost"] or data.get('splunk_password') or data.get('splunk_username')):
                payload = 'username={}&password={}'.format(quote_plus(data.get('splunk_username')), quote_plus(data.get("splunk_password")))
                splunk_server_port = data.get('splunk_rest_port') or '8089'
                splunk_verify_cert = is_true(VERIFY_SSL_KVSTORE)
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
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                response = requests.post(
                    splunk_url,
                    headers=headers,
                    data=payload,
                    verify=splunk_verify_cert,
                )
                if response.status_code == 401:
                    self.put_msg("Please verify the provided configurations.")
                    return False
                if not response.status_code == requests.codes.ok:
                    self.put_msg("Error occurred while saving the configuration. check splunkd.log")
                    return False
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
        return self.validate_splunk_kvstore_rest_credentials(data)

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
                    app_name, 'configs/conf-ta_threatquotient_add_on_settings'),
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
            app_name + '/TA_threatquotient_add_on_settings/proxy'
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
        return {"http" : uri, "https": uri}

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
            logger.info(response.text)
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
        required=True,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')

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

fields_splunk_rest_host = [
    field.RestField(
        'splunk_username',
        required=False,
        encrypted=False,
        default=None,
        validator=SplunkKvStoreRest()
    ),
    field.RestField(
        'splunk_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        )
    ),
    field.RestField(
        'splunk_rest_host_url',
        required=False,
        encrypted=False,
        default="localhost",
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        )
    ),
    field.RestField(
        'splunk_rest_port',
        required=False,
        encrypted=False,
        default=8089,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    )
]
model_splunk_rest_host = RestModel(
    fields_splunk_rest_host, name="splunk_rest_host")


endpoint = MultipleModel(
    'ta_threatquotient_add_on_settings',
    models=[
        model_proxy,
        model_logging,
        model_import_timeout,
        model_additional_parameters,
        model_splunk_rest_host
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
