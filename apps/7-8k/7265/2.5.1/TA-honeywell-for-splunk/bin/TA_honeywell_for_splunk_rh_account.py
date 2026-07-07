
import ta_honeywell_for_splunk_declare

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
        'retrive_data_from',
        required=True,
        encrypted=False,
        default="platform",
        validator=None
    ), 
    field.RestField(
        'organization_route',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
    	)
    ),
    field.RestField(
        'scadafence_server',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
        )
    ),
    field.RestField(
        'site_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
       )
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
      )
    ),
    field.RestField(
        'api_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
      )
   ),
   field.RestField(
        'page_size_asset',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
    	)
    ),
    field.RestField(
        'page_size_cves',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
    	)
    ),
    field.RestField(
        'api_retry_interval',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len= 0,
            max_len= 8192,
    	)
    ),
    field.RestField(
        'ssl_certification_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_honeywell_for_splunk_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
