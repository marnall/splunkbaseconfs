
import ta_digital_shadows_splunk_add_on_declare
from digital_shadows_account_validation import DigitalShadowsSearchlightUrlValidator, DigitalShadowsPortalUrlValidator, DigitalShadowsAccountIDValidator

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'account_id',
        required=True,
        encrypted=False,
        default=None,
        validator=DigitalShadowsAccountIDValidator()
    ),
    field.RestField(
        'ds_portal_url',
        required=True,
        encrypted=False,
        default="https://portal-digitalshadows.com",
        validator=DigitalShadowsPortalUrlValidator()
    ),
    field.RestField(
        'ds_searchlight_api_url',
        required=True,
        encrypted=False,
        default="https://api.searchlight.app",
        validator=DigitalShadowsSearchlightUrlValidator()
    ),
    field.RestField(
        'access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9]*$""",
        )
    ),
    field.RestField(
        'secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9]*$""",
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_digital_shadows_splunk_add_on_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
