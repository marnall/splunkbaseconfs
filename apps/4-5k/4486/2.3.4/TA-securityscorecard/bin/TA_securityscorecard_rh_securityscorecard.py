
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
        'interval',
        required=True,
        encrypted=False,
        default=86400,
        validator=validator.Number(
            max_val=604800, 
            min_val=86400, 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'securityscorecard_api_url',
        required=True,
        encrypted=False,
        default='https://api.securityscorecard.io',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'level_overall_change',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'level_factor_change',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'level_new_issue_change',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'domain',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'fetch_company_factors',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'fetch_company_issues',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'diff_override_own_overall',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'diff_override_own_factor',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'portfolio_ids',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'fetch_portfolio_overall',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'fetch_portfolio_factors',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'fetch_portfolio_issues',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'diff_override_portfolio_overall',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'diff_override_portfolio_factor',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'fetch_issue_level_data',
        required=False,
        encrypted=False,
        default=None,
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
    'securityscorecard',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
