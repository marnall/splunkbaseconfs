
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_cii_webhook_rh import CustomCIIWebhookIntegration
import logging

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=False,
        encrypted=False,
        default='',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            ), 
            validator.String(
                max_len=100, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'hec_token',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_cii',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='cisco:cii',
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=900, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'cii_json_text',
        required=False,
        encrypted=True,
        default='',
        validator=validator.Pattern(
            regex=r"""^(\s*|\s*\{.*\}\s*|\s*\[.*\]\s*)$""", 
        )
    ), 
    field.RestField(
        'cii_client_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'cii_api_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'cii_token_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'cii_audience',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'cii_client_secret',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'integration_method',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'hec_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^https:\/\/(?:(http-inputs[.-][^\/\s]+\.splunkcloud(gc)?\.com):(443|8088)|(?!.*http-inputs.*)(?!.*splunkcloud.*)[a-zA-Z0-9._-]+:\d+)\/services\/collector\/raw$""", 
            ), 
            validator.String(
                max_len=200, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'aws_access_key_id',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'aws_access_secret',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sqs_queue_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'cii_external_id',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        's3_bucket_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^s3://.+$""", 
        )
    ), 
    field.RestField(
        's3_bucket_region',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'sbg_cii_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomCIIWebhookIntegration,
    )
