
import ta_cyware_orchestrate_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

import re
import time
import requests
import modalert_push_alert_event_to_cyware_orchestrate_helper

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

UUID_REGEX = re.compile(
    r'^[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}$',
    re.IGNORECASE,
)
ULID_REGEX = re.compile(
    r'^[0-9A-HJKMNPQRSTVWXYZ]{26}$',
    re.IGNORECASE,
)

model_logging = RestModel(fields_logging, name='logging')


def url_validator(value, data, *args, **kwargs):
    """
    Check the user-provided Orchestrate URL to ensure that
        it begins with "https://" and has a length below 8192
        characters
    """
    if len(value) > 8192:
        raise validator.ValidationFailed("String length should be no longer than 8192")
    if not value.startswith("https://"):
        raise validator.ValidationFailed("Orchestrate URL must begin with \"https://\"")

def _is_uuid_or_ulid(s: str) -> bool:
    return bool(UUID_REGEX.fullmatch(s) or ULID_REGEX.fullmatch(s))


def access_id_validator(value, data, *args, **kwargs):
    """
    Check the user-provided Access ID to
        ensure it has the proper format
    """
    if not _is_uuid_or_ulid(value):
        raise validator.ValidationFailed(
            "Orchestrate Access ID must be either a UUID "
            "(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) or a ULID "
            "(26-character Crockford Base32: 0-9 A-H J K M N P Q R S T V W X Y Z)."
        )


def secret_key_validator(value, data, *args, **kwargs):
    """
    Check the user-provided Secret Key to
        ensure it has the proper format, and test
        authentication against the Orchestrate API
    """
    if not _is_uuid_or_ulid(value):
        raise validator.ValidationFailed(
            "Orchestrate Secret Key must be either a UUID "
            "(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) or a ULID "
            "(26-character Crockford Base32: 0-9 A-H J K M N P Q R S T V W X Y Z)."
        )
    try:
        expires = int(time.time() + 20)
        access_key = data.get('cyware_access_key', '')
        secret_key = data.get("cyware_secret_key", "")
        sign = modalert_push_alert_event_to_cyware_orchestrate_helper.generate_signature(expires, access_key, secret_key)
        security_params = {
            "AccessID": access_key,
            "Expires": expires,
            "Signature": sign
        }
        resp = requests.get(
            f"{data.get('cyware_url', '').strip('/')}/v1/integrations/apps/",
            params=security_params,
        )
    except Exception as e:
        raise validator.ValidationFailed(
            f"Failed to connect to Orchestrate API: {str(type(e))}: {str(e)}"
        )
    if resp.status_code != 200:
        raise validator.ValidationFailed(
            f"Failed to connect to Orchestrate API: {resp.text}"
        )


fields_additional_parameters = [
    field.RestField(
        'cyware_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.UserDefined(
            url_validator
        )
    ), 
    field.RestField(
        'cyware_access_key',
        required=True,
        encrypted=False,
        default='',
        validator=validator.UserDefined(
            access_id_validator
        )
    ), 
    field.RestField(
        'cyware_secret_key',
        required=True,
        encrypted=True,
        default='',
        validator=validator.UserDefined(
            secret_key_validator
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_cyware_orchestrate_settings',
    models=[
        model_proxy, 
        model_logging, 
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
