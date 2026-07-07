
import ta_hitachi_vsp_one_object_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


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


fields_additional_parameters = [
    field.RestField(
        'access_token_url',
        required=True,
        encrypted=False,
        default='https://admin.gms.{{cluster_name}}/ui/auth/realms/vsp-object/protocol/openid-connect/token',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='vsp-object-client',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'prometheus_base_url',
        required=True,
        encrypted=False,
        default='https://admin.{{prometheus_region}}.{{cluster_name}}/ui/prometheus/api/v1/query?query=',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'prometheus_region',
        required=True,
        encrypted=False,
        default='us-east-1',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'prometheus_cluster_name',
        required=True,
        encrypted=False,
        default='vsp1o.vspoc.sea.gpsecontent.local',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'csrf_token_generation_url',
        required=True,
        encrypted=False,
        default='https://admin.{{prometheus_region}}.{{cluster_name}}/mapi/v1/csrf',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_hitachi_vsp_one_object_settings',
    models=[
        model_logging, 
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
