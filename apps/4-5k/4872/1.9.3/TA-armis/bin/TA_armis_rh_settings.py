
import ta_armis_declare
import requests

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from requests.compat import quote_plus
import splunk.rest
from solnlib.utils import is_true

util.remove_http_proxy_env_vars()

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
                splunk_verify_cert = is_true(data.get('splunk_verify_cert'))
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
            return False
        except Exception:
            self.put_msg("Please verify the provided configurations.")
            return False
        return True

    def validate(self, value, data):
        return self.validate_splunk_kvstore_rest_credentials(data)

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

fields_splunk_rest_host = [
    field.RestField(
        'splunk_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        )
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
    ),
    field.RestField(
        'splunk_verify_cert',
        required=False,
        encrypted=False,
        default=None,
        validator=SplunkKvStoreRest()
    )
]
model_splunk_rest_host = RestModel(
    fields_splunk_rest_host, name="splunk_rest_host")



endpoint = MultipleModel(
    'ta_armis_settings',
    models=[
        model_proxy,
        model_logging,
        model_splunk_rest_host
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
