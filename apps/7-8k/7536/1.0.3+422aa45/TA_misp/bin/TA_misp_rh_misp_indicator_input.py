
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
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
        'misp_instance',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='ioc',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=True,
        encrypted=False,
        default='misp:ti:attributes',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9_:]+$""", 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
        )
    ), 
    field.RestField(
        'max_requests',
        required=False,
        encrypted=False,
        default=1000,
        validator=validator.Number(
            max_val=100000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'import_period',
        required=False,
        encrypted=False,
        default='180d',
        validator=validator.Pattern(
            regex=r"""^([0-9]+(d|m|y)|all)$""", 
        )
    ), 
    field.RestField(
        'types',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9,|\-_]+$""", 
        )
    ), 
    field.RestField(
        'to_ids',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'published',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'include_tags',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9,|\-:\.]+$""", 
        )
    ), 
    field.RestField(
        'exclude_tags',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9,|\-:\.]+$""", 
        )
    ), 
    field.RestField(
        'warning_list',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'continuous_importing',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'override_timestamps',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'normalize_field_names',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'normalized_field_prefix',
        required=False,
        encrypted=False,
        default='misp_',
        validator=validator.Pattern(
            regex=r"""^[0-9a-zA-Z_\-]+$""", 
        )
    ), 
    field.RestField(
        'expand_tags',
        required=False,
        encrypted=False,
        default=True,
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
    'misp_indicator_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
