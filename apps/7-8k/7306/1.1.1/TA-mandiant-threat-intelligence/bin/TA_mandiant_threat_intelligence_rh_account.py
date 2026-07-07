
import ta_mandiant_threat_intelligence_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from mati_validator import ValidateMatiAccount


util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'key_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=ValidateMatiAccount()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_mandiant_threat_intelligence_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
