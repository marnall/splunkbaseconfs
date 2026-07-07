
import ta_datiphy_policy_violation_response_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields_additional_parameters = [
    field.RestField(
        'security_center_email',
        required=True,
        encrypted=False,
        default='datiphy_soc@datiphy.com',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'soc_email_password',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'soc_email_recipient',
        required=True,
        encrypted=False,
        default='datiphy_soc@datiphy.com',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_datiphy_policy_violation_response_settings',
    models=[
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
