
import ta_jamf_pro_devices_and_analytics_by_loonsecio_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'jamf_pro_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'device_management_status',
        required=False,
        encrypted=False,
        default='MANAGED~NOTMANAGED',
        validator=None
    ), 
    field.RestField(
        'limit_inventory_time',
        required=True,
        encrypted=False,
        default='30',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'api_sections',
        required=False,
        encrypted=False,
        default='DISK_ENCRYPTION~GROUP_MEMBERSHIPS~APPLICATIONS~GENERAL~STORAGE~CONFIGURATION_PROFILES~SECURITY~EXTENSION_ATTRIBUTES~PURCHASING~HARDWARE~OPERATING_SYSTEM~PRINTERS~LOCAL_USER_ACCOUNTS~USER_AND_LOCATION',
        validator=None
    ), 
    field.RestField(
        'meta_builder',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'application_patching',
        required=False,
        encrypted=False,
        default='JAMFPATCH~LOONSECIO',
        validator=None
    ), 
    field.RestField(
        'share_analytics',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'vulnerability_detections',
        required=False,
        encrypted=False,
        default='apps~os',
        validator=None
    ), 
    field.RestField(
        'vulnerability_requirements',
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
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'jamf_mac_devices',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
