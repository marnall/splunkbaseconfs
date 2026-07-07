# pylint: disable=missing-module-docstring
# pylint: disable=invalid-name
import import_declare_test  # pylint: disable=unused-import
from virustotal.core import validators
from virustotal.core import constants

# pylint: disable=import-error
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging


util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None,
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        ),
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        ),
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        ),
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None,
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'virustotal_api_key',
        required=True,
        encrypted=True,
        default='',
        validator=validators.ValidateAPIKey(),
    ),
    field.RestField(
        'virustotal_cache_ttl',
        required=True,
        default='30',
        validator=validators.ValidateTTL(),
    ),
]
model_additional_parameters = RestModel(
    fields_additional_parameters, name='additional_parameters'
)


fields_correlation_parameters = [
    field.RestField(
        'virustotal_data_freshness',
        required=True,
        default='1',
        validator=validator.Number(
            min_val=1,
            max_val=90,
        ),
    )
]
model_correlation_parameters = RestModel(
    fields_correlation_parameters, name='correlation_parameters'
)


endpoint = MultipleModel(
    constants.SETTINGS_FILE,
    models=[
        model_proxy,
        model_logging,
        model_additional_parameters,
        model_correlation_parameters,
    ],
)


if __name__ == '__main__':
  logging.getLogger().addHandler(logging.NullHandler())
  admin_external.handle(
      endpoint,
      handler=AdminExternalHandler,
  )
