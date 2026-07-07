
import import_declare_test

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


fields_thousandeyes_free_trial = [
    field.RestField(
        'trial_step_1',
        required=False,
        encrypted=False,
        default='Submit the ThousandEyes free trial form',
        validator=None
    ), 
    field.RestField(
        'trial_step_2',
        required=False,
        encrypted=False,
        default='Wait for an email with the activation link',
        validator=None
    ), 
    field.RestField(
        'trial_step_3',
        required=False,
        encrypted=False,
        default='Set your password',
        validator=None
    ), 
    field.RestField(
        'trial_step_4',
        required=False,
        encrypted=False,
        default='Create the ThousandEyes test',
        validator=None
    ), 
    field.RestField(
        'create_test_docs_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_thousandeyes_free_trial = RestModel(fields_thousandeyes_free_trial, name='thousandeyes_free_trial')


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_auth_type',
        required=True,
        encrypted=False,
        default='basic',
        validator=None
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
    ), 
    field.RestField(
        'proxy_type',
        required=True,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_cert',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""-----BEGIN CERTIFICATE-----([\r\n]+)([0-9a-zA-Z\+\/\=\r\n]+)-----END CERTIFICATE-----""", 
        )
    ), 
    field.RestField(
        'proxy_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=4096, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9:][a-zA-Z0-9\.\-:]+$""", 
            )
        )
    ), 
    field.RestField(
        'proxy_port',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
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
            regex=r"""^DEBUG|INFO|WARN|ERROR|CRITICAL$""", 
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'ta_cisco_thousandeyes_settings',
    models=[
        model_thousandeyes_free_trial, 
        model_proxy, 
        model_logging
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
