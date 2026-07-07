
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.splunk_aoblib.rest_migration import ConfigMigrationHandler
import logging
from splunk import admin

from mandiant_validator import ValidateAccountType
from common.utility import read_conf_file
import common.log as log

util.remove_http_proxy_env_vars()

logger = log.get_logger(__file__)

class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class AccountHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """
    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = read_conf_file(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        input_type_list = ["mandiant_security_validation_reporting", "mandiant_advantage_indicators","mandiant_advantage_monitoring_alerts"]
        for _input in created_inputs:
            mandiant_input = _input.split('://')
            if mandiant_input[0] in input_type_list:
                configured_account = inputs_file.get(_input).get('mandiant_advantage_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(mandiant_input[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "\"{}\" cannot be deleted because it is in use".format(self.callerArgs.id))
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'account_type',
        required=True,
        encrypted=False,
        default='mandiant_advantage',
        validator=ValidateAccountType()
    ), 
    field.RestField(
        'endpoint_url',
        required=True,
        encrypted=False,
        default='api.intelligence.mandiant.com',
        validator=validator.AllOf(
            validator.String(
                max_len=200, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^(?!\w+:\/\/).*""", 
            )
        )
    ), 
    field.RestField(
        'validation_verify_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'client_id',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'access_key',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'secret_key',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'api_token',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'validation_api_version',
        required=False,
        encrypted=False,
        default='v2',
        validator=validator.String(
            max_len=3, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_mandiant_advantage_account',
    model,
    config_name='account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
