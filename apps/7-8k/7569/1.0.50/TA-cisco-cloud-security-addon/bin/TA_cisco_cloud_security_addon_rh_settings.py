
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


fields_addon_settings = [
    field.RestField(
        'max_concurrent_threads',
        required=True,
        encrypted=False,
        default=1,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[0-9]+$""", 
            ), 
            validator.Number(
                max_val=10, 
                min_val=1, 
            )
        )
    )
]
model_addon_settings = RestModel(fields_addon_settings, name='addon_settings')


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
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?=.{1,253}$)(?!-)([a-zA-Z0-9-]{1,63}(?<!-).)*([a-zA-Z0-9-]{1,63})(?<!-)$)|(^((25[0-5]|(2[0-4]|1[0-9]|[1-9]?)[0-9]).){3}(25[0-5]|(2[0-4]|1[0-9]|[1-9]?)[0-9])$)|(^([0-9a-fA-F]{1,4}:){7}([0-9a-fA-F]{1,4}|:)$)|(^([0-9a-fA-F]{1,4}:){1,7}:$|(^([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}$)|(^([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}$)|(^([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}$)|(^([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}$)|(^([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}$)|(^([0-9a-fA-F]{1,4}:):((:[0-9a-fA-F]{1,4}){1,6})$)|(^:((:[0-9a-fA-F]{1,4}){1,7}|:)$)|(^([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1[0-9]|[1-9]?)[0-9]).){3}(25[0-5]|(2[0-4]|1[0-9]|[1-9]?)[0-9])$))""", 
            ), 
            validator.String(
                max_len=4096, 
                min_len=0, 
            )
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
        validator=validator.Pattern(
            regex=r"""^DEBUG|INFO|WARNING|ERROR|CRITICAL$""", 
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'ta_cisco_cloud_security_addon_settings',
    models=[
        model_addon_settings, 
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
