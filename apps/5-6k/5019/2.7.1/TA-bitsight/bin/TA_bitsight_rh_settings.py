
import import_declare_test  # noqa F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from bitsight_utils import BitsightMacroManager, ValidateBitsightInstance


util.remove_http_proxy_env_vars()


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
            max_len=4096,
            min_len=0,
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50,
            min_len=0,
        )
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
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
        validator=validator.Pattern(
            regex=r"""^DEBUG|INFO|WARNING|ERROR|CRITICAL$""",
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_authentication = [
    field.RestField(
        'api_url',
        required=True,
        encrypted=False,
        default='https://api.bitsighttech.com/',
        validator=validator.Pattern(
            regex=r"""^https://.*""",
        )
    ),
    field.RestField(
        'bitsight_api_token',
        required=True,
        encrypted=True,
        default='',
        validator=ValidateBitsightInstance()
    )
]
model_authentication = RestModel(fields_authentication, name='authentication')


fields_wfh = [
    field.RestField(
        'custom_command_index',
        required=False,
        encrypted=False,
        default='',
        validator=BitsightMacroManager()
    )
]
model_wfh = RestModel(fields_wfh, name='wfh')


endpoint = MultipleModel(
    'ta_bitsight_settings',
    models=[
        model_proxy,
        model_logging,
        model_authentication,
        model_wfh
    ],
    need_reload=False,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
