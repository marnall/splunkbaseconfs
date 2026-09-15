
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


fields_aws_account = [
    field.RestField(
        'aws_access_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=128, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'aws_secret_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=512, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'aws_session_token',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'region',
        required=True,
        encrypted=False,
        default='us-east-1',
        validator=None
    ), 
    field.RestField(
        'wipe_credentials',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    )
]
model_aws_account = RestModel(fields_aws_account, name='aws_account')


fields_deployment = [
    field.RestField(
        'hec_url',
        required=True,
        encrypted=False,
        default='https://http-inputs-<stack>.splunkcloud.com',
        validator=validator.Pattern(
            regex=r"""^https?://.+""", 
        )
    ), 
    field.RestField(
        'hec_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=128, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='edr',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=True,
        encrypted=False,
        default='edr:json',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'routes',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'auto_sourcetype',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    ), 
    field.RestField(
        'hec_raw',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ), 
    field.RestField(
        'bucket',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-z0-9.\-]{3,63}$""", 
        )
    ), 
    field.RestField(
        'prefix',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=1024, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'suffix',
        required=False,
        encrypted=False,
        default='.gz',
        validator=validator.String(
            max_len=64, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'missed_prefix',
        required=False,
        encrypted=False,
        default='_splunk_missed/',
        validator=validator.String(
            max_len=128, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'function_name',
        required=True,
        encrypted=False,
        default='s3-to-splunk-hec',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9\-_]{1,64}$""", 
        )
    ), 
    field.RestField(
        'role_name',
        required=True,
        encrypted=False,
        default='s3-to-splunk-hec-role',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9+=,.@\-_]{1,64}$""", 
        )
    ), 
    field.RestField(
        'tags',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=1024, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'lambda_timeout',
        required=True,
        encrypted=False,
        default='900',
        validator=validator.Pattern(
            regex=r"""^[0-9]{1,3}$""", 
        )
    ), 
    field.RestField(
        'lambda_memory',
        required=True,
        encrypted=False,
        default='512',
        validator=validator.Pattern(
            regex=r"""^[0-9]{2,5}$""", 
        )
    ), 
    field.RestField(
        'reserved_concurrency',
        required=True,
        encrypted=False,
        default='20',
        validator=validator.Pattern(
            regex=r"""^[0-9]{1,4}$""", 
        )
    ), 
    field.RestField(
        'batch_max_bytes',
        required=True,
        encrypted=False,
        default='800000',
        validator=validator.Pattern(
            regex=r"""^[0-9]{3,7}$""", 
        )
    ), 
    field.RestField(
        'gzip_post',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    ), 
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    )
]
model_deployment = RestModel(fields_deployment, name='deployment')


fields_license = [
    field.RestField(
        'license_key',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_license = RestModel(fields_license, name='license')


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
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
                regex=r"""^[a-zA-Z]\w*$""", 
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
            is_int=True, 
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


endpoint = MultipleModel(
    's3_lambda_deployer_settings',
    models=[
        model_aws_account, 
        model_deployment, 
        model_license, 
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
