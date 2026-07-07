
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


fields_azure2blob = [
    field.RestField(
        'AZ_BLOB_CONTAINER',
        required=True,
        encrypted=False,
        default='splunk-cold2frozen-archives',
        validator=None
    ), 
    field.RestField(
        'AZ_BLOB_CONNECTION_STRING',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'AZ_STORAGE_TABLE_NAME',
        required=True,
        encrypted=False,
        default='splunkdb',
        validator=None
    ), 
    field.RestField(
        'AZ_BLOB_STRUCTURE',
        required=True,
        encrypted=False,
        default='index_name',
        validator=None
    ), 
    field.RestField(
        'AZ_COMPRESS',
        required=True,
        encrypted=False,
        default='False',
        validator=None
    ), 
    field.RestField(
        'remote_username',
        required=False,
        encrypted=False,
        default='admin',
        validator=None
    ), 
    field.RestField(
        'remote_password',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    )
]
model_azure2blob = RestModel(fields_azure2blob, name='azure2blob')


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


endpoint = MultipleModel(
    'azure2blob_settings',
    models=[
        model_azure2blob, 
        model_logging
    ],
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
