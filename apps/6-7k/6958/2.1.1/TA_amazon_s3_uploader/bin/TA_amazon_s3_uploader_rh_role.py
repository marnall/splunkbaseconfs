
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[0-9|a-z|A-Z][\w\- ,]*$""", 
            ), 
            validator.String(
                max_len=50, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'aws_arn',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^arn:aws(?:-(?:cn|us-gov))?:iam::[\d]{12}:role/[A-Za-z0-9_+=,.@-]+$""", 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_amazon_s3_uploader_role',
    model,
    config_name='role',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
