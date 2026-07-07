
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from cymru_helpers.validators import CorrelationValidator, SplunkKvStoreRest
import logging

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
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_splunk_rest_host = [
    field.RestField(
        'collection_type',
        required=True,
        encrypted=False,
        default='index',
        validator=SplunkKvStoreRest()
    ), 
    field.RestField(
        'cymru_indicator_indices_macro',
        required=True,
        encrypted=False,
        default='main',
        validator=None
    ), 
    field.RestField(
        'splunk_rest_host_url',
        required=False,
        encrypted=False,
        default='localhost',
        validator=validator.AllOf(
            validator.String(
                max_len=8192, 
                min_len=0, 
            ), 
            validator.Pattern(
                regex=r"""^(?!\w+:\/\/).*""", 
            )
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
    )
]
model_splunk_rest_host = RestModel(fields_splunk_rest_host, name='splunk_rest_host')


fields_correlation_settings = [
    field.RestField(
        'required_disable_checkbox',
        required=True,
        encrypted=False,
        default=True,
        validator=CorrelationValidator()
    ), 
    field.RestField(
        'enabled_indicator_types',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'match_type',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'datamodel_list',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'target_splunk_query_domain',
        required=False,
        encrypted=False,
        default='index=main sourcetype!=*team_cymru_*',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'target_fields_to_match_domain',
        required=False,
        encrypted=False,
        default='domain, src, dest',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'target_splunk_query_ip',
        required=False,
        encrypted=False,
        default='index=main sourcetype!=*team_cymru_*',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'target_fields_to_match_ip',
        required=False,
        encrypted=False,
        default='ip, src, dest',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_correlation_settings = RestModel(fields_correlation_settings, name='correlation_settings')


endpoint = MultipleModel(
    'teamcymruscoutappforsplunk_settings',
    models=[
        model_proxy, 
        model_logging, 
        model_splunk_rest_host, 
        model_correlation_settings
    ],
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
