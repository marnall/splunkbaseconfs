
import import_declare_test    # noqa: F401
import os
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunk import admin
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.splunk_aoblib.rest_migration import ConfigMigrationHandler
from dataminr_validator import AccountValidator
from solnlib.conf_manager import ConfManager
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'api_version',
        required=True,
        encrypted=False,
        default='v4',
        validator=None
    ),
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator(),
    ),
    field.RestField(
        'access_token',
        required=False,
        encrypted=True,
        default=None,
    ),
    field.RestField(
        'refresh_token',
        required=False,
        encrypted=True,
        default=None,
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'dataminr_account',
    model,
    config_name='account'
)

class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()

class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(confInfo)

    def read_conf_file(self, session_key: str, app_name: str, conf_fname:str) -> dict:
        """
        Get conf file content with conf_manager.

        :param session_key: Splunk session key
        :param conf_file: conf file name
        :param stanza: If stanza name is present then return only that stanza,
                        otherwise return all stanza
        """
        conf_file = ConfManager(
            session_key,
            app_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app_name, conf_fname),
        ).get_conf(conf_fname)
        return conf_file.get_all(only_current_app=True)

    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key  # noqa: F405
        path = os.path.abspath(__file__)
        app_name = path.split('/')[-3] if '/' in path else path.split('\\')[-3]
        inputs_file = self.read_conf_file(session_key, app_name, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        for each in created_inputs:
            each_dataminr_input = each.split("://")
            configured_account = inputs_file.get(each).get("dataminr_account")
            if configured_account == self.callerArgs.id:
                input_list.append(each_dataminr_input[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(  # noqa: F405
                "Account '{}' will not be deleted because it is linked with the"
                " following inputs: {}".format(self.callerArgs.id, ", ".join(input_list))
            )
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AccountHandler
    )
